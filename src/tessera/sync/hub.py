"""Hub side: verify signed batches and store them idempotently."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from tessera.models import Observation
from tessera.sync import signing
from tessera.sync.batch import Ack, SyncBatch, open_batch, signature_bytes, signing_message
from tessera.sync.errors import AuthError

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    ingest_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id TEXT NOT NULL,
    edge_seq INTEGER NOT NULL,
    schema_version INTEGER NOT NULL,
    payload TEXT NOT NULL,
    UNIQUE (edge_id, edge_seq)
);
CREATE TABLE IF NOT EXISTS edges (
    edge_id TEXT PRIMARY KEY,
    acked_seq INTEGER NOT NULL
);
"""


class HubStore:
    """SQLite store of observations received from edges. One short-lived connection per call,
    so it is safe to use from a threaded web server."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        conn = self._connect()
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
        finally:
            conn.close()

    @property
    def path(self) -> str:
        return self._path

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=10)

    def acked_seq(self, edge_id: str) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT acked_seq FROM edges WHERE edge_id = ?", (edge_id,)
            ).fetchone()
        finally:
            conn.close()
        return int(row[0]) if row else 0

    def apply(self, edge_id: str, rows: Sequence[tuple[int, Observation]]) -> int:
        """Insert rows (duplicates ignored), advance the edge cursor, return the cursor."""
        conn = self._connect()
        try:
            with conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO events (edge_id, edge_seq, schema_version, payload) "
                    "VALUES (?, ?, ?, ?)",
                    [
                        (edge_id, seq, obs.schema_version, obs.model_dump_json())
                        for seq, obs in rows
                    ],
                )
                conn.execute(
                    "INSERT INTO edges (edge_id, acked_seq) VALUES (?, ?) ON CONFLICT(edge_id) "
                    "DO UPDATE SET acked_seq = MAX(acked_seq, excluded.acked_seq)",
                    (edge_id, rows[-1][0]),
                )
                (acked,) = conn.execute(
                    "SELECT acked_seq FROM edges WHERE edge_id = ?", (edge_id,)
                ).fetchone()
        finally:
            conn.close()
        return int(acked)

    def count(self) -> int:
        conn = self._connect()
        try:
            (total,) = conn.execute("SELECT COUNT(*) FROM events").fetchone()
        finally:
            conn.close()
        return int(total)


class Hub:
    """Verifies batches from trusted edges and stores them."""

    def __init__(self, store: HubStore, trusted_keys: Mapping[str, Ed25519PublicKey]) -> None:
        self._store = store
        self._keys = dict(trusted_keys)

    @property
    def store(self) -> HubStore:
        return self._store

    def receive(self, batch: SyncBatch) -> Ack:
        """Verify, then store. Returns the edge cursor the hub now holds.

        A batch that starts after a gap is not stored; the returned cursor tells the edge
        where to resume.
        """
        key = self._keys.get(batch.edge_id)
        if key is None:
            raise AuthError("unknown edge")
        message = signing_message(
            batch.edge_id, batch.first_seq, batch.last_seq, batch.count, batch.sha256
        )
        if not signing.verify(key, signature_bytes(batch), message):
            raise AuthError("invalid signature")
        rows = open_batch(batch)
        acked = self._store.acked_seq(batch.edge_id)
        if batch.first_seq > acked + 1:
            return Ack(edge_id=batch.edge_id, acked_seq=acked)
        return Ack(edge_id=batch.edge_id, acked_seq=self._store.apply(batch.edge_id, rows))
