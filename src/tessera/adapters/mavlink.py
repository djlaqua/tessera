"""MAVLink 2 adapter (GLOBAL_POSITION_INT).

Notes:
- MAVLink altitude (`alt`) is above mean sea level, so it is tagged `AltitudeReference.MSL`.
- GLOBAL_POSITION_INT carries only `time_boot_ms`, not wall time. `observed_at` is therefore
  the receive time from the injected clock, and `time_boot_ms` is kept as an attribute.
- Frames are not authenticated unless MAVLink signing is used. Pass `signing_key` (32 bytes)
  to require valid signatures: unsigned, wrongly signed and replayed frames are rejected
  (ADR-008). Without a key the link must be treated as untrusted.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from pymavlink.dialects.v20 import common as mavlink2

from tessera.errors import AdapterError
from tessera.models import AltitudeReference, EntityType, Observation, Position, Velocity

MAX_CHUNK_BYTES = 65_536
SIGNING_KEY_BYTES = 32
_HEADING_UNKNOWN = 65_535
_MESSAGE_TYPE = "GLOBAL_POSITION_INT"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class MavlinkAdapter:
    """Stateful MAVLink 2 stream parser. Use one instance per link."""

    name = "mavlink"

    def __init__(
        self,
        source_id: str,
        *,
        entity_type: EntityType = EntityType.UAV,
        clock: Callable[[], datetime] = _utc_now,
        signing_key: bytes | None = None,
    ) -> None:
        if signing_key is not None and len(signing_key) != SIGNING_KEY_BYTES:
            raise ValueError(f"signing_key must be {SIGNING_KEY_BYTES} bytes")
        self._source_id = source_id
        self._entity_type = entity_type
        self._clock = clock
        self._mav = mavlink2.MAVLink(None)
        self._mav.robust_parsing = True
        if signing_key is not None:
            self._mav.signing.secret_key = signing_key
            self._mav.signing.allow_unsigned_callback = lambda _mav, _message_id: False
        self.rejected = 0

    def parse(self, raw: bytes) -> list[Observation]:
        if len(raw) > MAX_CHUNK_BYTES:
            raise AdapterError(f"chunk of {len(raw)} bytes exceeds {MAX_CHUNK_BYTES}")
        messages = self._mav.parse_buffer(raw) or []
        observations: list[Observation] = []
        for message in messages:
            if message.get_type() == "BAD_DATA":
                self.rejected += 1
                continue
            if message.get_type() != _MESSAGE_TYPE:
                continue
            observation = self._to_observation(message)
            if observation is None:
                self.rejected += 1
            else:
                observations.append(observation)
        return observations

    def _to_observation(self, message: Any) -> Observation | None:
        if message.lat == 0 and message.lon == 0:
            return None  # no GNSS fix reported
        speed_mps = math.hypot(message.vx, message.vy) / 100.0
        course_deg = (math.degrees(math.atan2(message.vy, message.vx)) + 360.0) % 360.0
        attributes: dict[str, str | int | float | bool] = {
            "time_boot_ms": int(message.time_boot_ms),
            "relative_alt_m": message.relative_alt / 1000.0,
        }
        if message.hdg != _HEADING_UNKNOWN:
            attributes["heading_deg"] = message.hdg / 100.0
        now = self._clock()
        try:
            return Observation(
                source_id=self._source_id,
                entity_id=f"sys{message.get_srcSystem()}.comp{message.get_srcComponent()}",
                entity_type=self._entity_type,
                observed_at=now,
                ingested_at=now,
                position=Position(
                    lat=message.lat / 1e7,
                    lon=message.lon / 1e7,
                    alt_m=message.alt / 1000.0,
                    alt_ref=AltitudeReference.MSL,
                ),
                velocity=Velocity(course_deg=course_deg, speed_mps=speed_mps),
                attributes=attributes,
            )
        except ValidationError:
            return None
