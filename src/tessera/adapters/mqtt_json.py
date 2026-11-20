"""MQTT JSON payload adapter.

Parses one JSON object per payload. Transport (broker connection) is out of scope here;
feed this adapter the payload bytes from any MQTT client.

Expected payload:
    {"entity_id": "pump-3", "entity_type": "sensor", "lat": 48.1, "lon": 11.5,
     "alt_m": 520.0, "accuracy_m": 3.0, "time": "2026-11-20T09:00:00Z",
     "attributes": {"battery_pct": 87}}
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from tessera.errors import AdapterError
from tessera.models import (
    EntityType,
    Identifier,
    Observation,
    Position,
    Scalar,
)

MAX_PAYLOAD_BYTES = 16_384


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: Identifier
    entity_type: EntityType = EntityType.SENSOR
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    alt_m: float | None = None
    accuracy_m: float | None = Field(default=None, ge=0.0)
    time: AwareDatetime | None = None
    attributes: dict[str, Scalar] = Field(default_factory=dict)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class MqttJsonAdapter:
    """Stateless JSON payload parser."""

    name = "mqtt-json"

    def __init__(self, source_id: str, *, clock: Callable[[], datetime] = _utc_now) -> None:
        self._source_id = source_id
        self._clock = clock
        self.rejected = 0

    def parse(self, raw: bytes) -> list[Observation]:
        if len(raw) > MAX_PAYLOAD_BYTES:
            raise AdapterError(f"payload of {len(raw)} bytes exceeds {MAX_PAYLOAD_BYTES}")
        try:
            payload = _Payload.model_validate_json(raw)
            return [self._to_observation(payload)]
        except (ValidationError, ValueError):
            self.rejected += 1
            return []

    def _to_observation(self, payload: _Payload) -> Observation:
        now = self._clock()
        fields: dict[str, Any] = {
            "source_id": self._source_id,
            "entity_id": payload.entity_id,
            "entity_type": payload.entity_type,
            "observed_at": payload.time or now,
            "ingested_at": now,
            "position": Position(lat=payload.lat, lon=payload.lon, alt_m=payload.alt_m),
            "position_accuracy_m": payload.accuracy_m,
            "attributes": payload.attributes,
        }
        return Observation(**fields)
