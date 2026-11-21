"""Canonical, immutable data model."""

from __future__ import annotations

from datetime import UTC
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

MAX_ATTRIBUTES = 32
MAX_ATTRIBUTE_VALUE_LEN = 256
SCHEMA_VERSION = 1

Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:\-]+$")]
Scalar = str | int | float | bool


class EntityType(StrEnum):
    UAV = "uav"
    VESSEL = "vessel"
    GROUND = "ground"
    SENSOR = "sensor"


class AltitudeReference(StrEnum):
    """Vertical datum of `Position.alt_m`."""

    ELLIPSOID = "ellipsoid"
    MSL = "msl"


class Position(BaseModel):
    """WGS84 position. `alt_m` is in meters relative to `alt_ref` (ellipsoid by default)."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    alt_m: float | None = Field(default=None, ge=-1000.0, le=100_000.0)
    alt_ref: AltitudeReference = AltitudeReference.ELLIPSOID


class Velocity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    course_deg: float = Field(ge=0.0, lt=360.0)
    speed_mps: float = Field(ge=0.0, le=2_000.0)


class Observation(BaseModel):
    """One timestamped observation of an entity from one source."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    id: UUID = Field(default_factory=uuid4)
    source_id: Identifier
    entity_id: Identifier
    entity_type: EntityType
    observed_at: AwareDatetime
    ingested_at: AwareDatetime
    position: Position | None = None
    velocity: Velocity | None = None
    position_accuracy_m: float | None = Field(default=None, ge=0.0)
    attributes: dict[str, Scalar] = Field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    @field_validator("observed_at", "ingested_at")
    @classmethod
    def _to_utc(cls, value: AwareDatetime) -> AwareDatetime:
        return value.astimezone(UTC)

    @field_validator("attributes")
    @classmethod
    def _bound_attributes(cls, value: dict[str, Scalar]) -> dict[str, Scalar]:
        if len(value) > MAX_ATTRIBUTES:
            raise ValueError(f"at most {MAX_ATTRIBUTES} attributes allowed")
        for key, item in value.items():
            if len(key) > 64:
                raise ValueError("attribute key too long")
            if isinstance(item, str) and len(item) > MAX_ATTRIBUTE_VALUE_LEN:
                raise ValueError("attribute value too long")
        return value
