"""AIS adapter: NMEA 0183 `!AIVDM`/`!AIVDO` class A position reports (types 1, 2, 3).

Single-sentence messages only. Multi-sentence messages (for example type 5) and other
message types are ignored. Checksums are verified; bad sentences are counted and dropped.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import ValidationError

from tessera.errors import AdapterError
from tessera.models import EntityType, Observation, Position, Velocity

MAX_CHUNK_BYTES = 16_384
_KNOTS_TO_MPS = 1852.0 / 3600.0
_SENTENCE = re.compile(
    r"^!AIVD[MO],(?P<count>\d),(?P<index>\d),(?P<seq>\d?),(?P<chan>[AB12]?),"
    r"(?P<payload>[0-9:;<=>?@A-Wa-w`]+),(?P<fill>[0-5])\*(?P<sum>[0-9A-Fa-f]{2})$"
)
_POSITION_TYPES = {1, 2, 3}
_MIN_BITS = 137
_LON_UNAVAILABLE = 181 * 600_000
_LAT_UNAVAILABLE = 91 * 600_000
_SOG_UNAVAILABLE = 1023
_COG_UNAVAILABLE = 3600


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _checksum(body: str) -> int:
    value = 0
    for char in body:
        value ^= ord(char)
    return value


def _unarmor(payload: str, fill_bits: int) -> str | None:
    bits: list[str] = []
    for char in payload:
        value = ord(char) - 48
        if value > 40:
            value -= 8
        if not 0 <= value <= 63:
            return None
        bits.append(format(value, "06b"))
    joined = "".join(bits)
    return joined[: len(joined) - fill_bits] if fill_bits else joined


def _unsigned(bits: str, start: int, length: int) -> int:
    return int(bits[start : start + length], 2)


def _signed(bits: str, start: int, length: int) -> int:
    value = _unsigned(bits, start, length)
    return value - (1 << length) if value >= 1 << (length - 1) else value


class AisAdapter:
    """Stateless NMEA AIS parser."""

    name = "ais"

    def __init__(self, source_id: str, *, clock: Callable[[], datetime] = _utc_now) -> None:
        self._source_id = source_id
        self._clock = clock
        self.rejected = 0

    def parse(self, raw: bytes) -> list[Observation]:
        if len(raw) > MAX_CHUNK_BYTES:
            raise AdapterError(f"chunk of {len(raw)} bytes exceeds {MAX_CHUNK_BYTES}")
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            self.rejected += 1
            return []
        observations: list[Observation] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            observation = self._parse_sentence(line)
            if observation is not None:
                observations.append(observation)
        return observations

    def _parse_sentence(self, line: str) -> Observation | None:
        match = _SENTENCE.match(line)
        if match is None or int(match["sum"], 16) != _checksum(line[1 : line.rindex("*")]):
            self.rejected += 1
            return None
        if match["count"] != "1" or match["index"] != "1":
            return None  # multi-sentence messages are not supported
        bits = _unarmor(match["payload"], int(match["fill"]))
        if bits is None or len(bits) < _MIN_BITS or _unsigned(bits, 0, 6) not in _POSITION_TYPES:
            return None
        return self._decode_position(bits)

    def _decode_position(self, bits: str) -> Observation | None:
        mmsi = _unsigned(bits, 8, 30)
        sog_raw = _unsigned(bits, 50, 10)
        lon_raw = _signed(bits, 61, 28)
        lat_raw = _signed(bits, 89, 27)
        cog_raw = _unsigned(bits, 116, 12)
        if lon_raw == _LON_UNAVAILABLE or lat_raw == _LAT_UNAVAILABLE:
            self.rejected += 1
            return None
        velocity = None
        if sog_raw != _SOG_UNAVAILABLE and cog_raw != _COG_UNAVAILABLE and cog_raw < 3600:
            velocity = Velocity(course_deg=cog_raw / 10.0, speed_mps=sog_raw / 10.0 * _KNOTS_TO_MPS)
        now = self._clock()
        try:
            return Observation(
                source_id=self._source_id,
                entity_id=f"mmsi{mmsi}",
                entity_type=EntityType.VESSEL,
                observed_at=now,
                ingested_at=now,
                position=Position(lat=lat_raw / 600_000.0, lon=lon_raw / 600_000.0),
                velocity=velocity,
            )
        except ValidationError:
            self.rejected += 1
            return None
