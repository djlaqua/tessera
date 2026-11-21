"""Signed, compressed batches of observations.

Wire format: a JSON envelope. The payload is zlib-compressed lines of `<seq>\\t<observation json>`.
The Ed25519 signature covers a domain tag, the edge id, the sequence range, the count and the
payload SHA-256, so any change to the envelope or payload is detected.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import zlib
from collections.abc import Sequence

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tessera.models import Identifier, Observation
from tessera.sync import signing
from tessera.sync.errors import SyncError

MAX_BATCH_EVENTS = 500
MAX_PAYLOAD_B64_CHARS = 1_400_000
MAX_DECOMPRESSED_BYTES = 8 * 1024 * 1024
_DOMAIN = "tessera-sync-v1"


class SyncBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: Identifier
    first_seq: int = Field(ge=1)
    last_seq: int = Field(ge=1)
    count: int = Field(ge=1, le=MAX_BATCH_EVENTS)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_b64: str = Field(max_length=MAX_PAYLOAD_B64_CHARS)
    signature_b64: str = Field(max_length=256)


class Ack(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: Identifier
    acked_seq: int = Field(ge=0)


def signing_message(edge_id: str, first_seq: int, last_seq: int, count: int, sha256: str) -> bytes:
    return f"{_DOMAIN}|{edge_id}|{first_seq}|{last_seq}|{count}|{sha256}".encode()


def build_batch(
    edge_id: str, rows: Sequence[tuple[int, Observation]], key: Ed25519PrivateKey
) -> SyncBatch:
    """Build and sign a batch from (seq, observation) rows in ascending order."""
    if not rows:
        raise SyncError("cannot build an empty batch")
    if len(rows) > MAX_BATCH_EVENTS:
        raise SyncError(f"batch exceeds {MAX_BATCH_EVENTS} events")
    lines = "\n".join(f"{seq}\t{obs.model_dump_json()}" for seq, obs in rows).encode()
    payload = zlib.compress(lines, 6)
    digest = hashlib.sha256(payload).hexdigest()
    first_seq, last_seq = rows[0][0], rows[-1][0]
    signature = signing.sign(key, signing_message(edge_id, first_seq, last_seq, len(rows), digest))
    return SyncBatch(
        edge_id=edge_id,
        first_seq=first_seq,
        last_seq=last_seq,
        count=len(rows),
        sha256=digest,
        payload_b64=base64.b64encode(payload).decode("ascii"),
        signature_b64=base64.b64encode(signature).decode("ascii"),
    )


def _b64(value: str, what: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SyncError(f"{what} is not valid base64") from exc


def signature_bytes(batch: SyncBatch) -> bytes:
    return _b64(batch.signature_b64, "signature")


def open_batch(batch: SyncBatch) -> list[tuple[int, Observation]]:
    """Decode and validate a batch. Signatures are checked by `Hub.receive`, not here."""
    payload = _b64(batch.payload_b64, "payload")
    if hashlib.sha256(payload).hexdigest() != batch.sha256:
        raise SyncError("payload hash mismatch")
    decompressor = zlib.decompressobj()
    try:
        raw = decompressor.decompress(payload, MAX_DECOMPRESSED_BYTES)
    except zlib.error as exc:
        raise SyncError("payload is not valid zlib data") from exc
    if decompressor.unconsumed_tail or not decompressor.eof:
        raise SyncError("payload truncated or too large after decompression")
    rows: list[tuple[int, Observation]] = []
    previous = batch.first_seq - 1
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SyncError("payload is not UTF-8") from exc
    for line in text.split("\n"):
        seq_text, _, body = line.partition("\t")
        try:
            seq = int(seq_text)
            observation = Observation.model_validate_json(body)
        except (ValueError, ValidationError) as exc:
            raise SyncError("malformed row in batch") from exc
        if seq <= previous or seq > batch.last_seq:
            raise SyncError("sequence numbers out of order or out of range")
        previous = seq
        rows.append((seq, observation))
    if len(rows) != batch.count or rows[0][0] != batch.first_seq or rows[-1][0] != batch.last_seq:
        raise SyncError("batch header does not match contents")
    return rows
