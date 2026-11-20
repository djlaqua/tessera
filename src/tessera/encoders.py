"""Output encoders: Cursor-on-Target XML and GeoJSON."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from tessera.models import AltitudeReference, EntityType, Observation

_COT_UNKNOWN = "9999999.0"
# VERIFY against the CoT type schema before relying on these mappings.
_COT_TYPES: dict[EntityType, str] = {
    EntityType.UAV: "a-u-A",
    EntityType.VESSEL: "a-u-S",
    EntityType.GROUND: "a-u-G",
    EntityType.SENSOR: "a-u-G",
}


def _cot_time(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{utc.microsecond // 1000:03d}Z"


def to_cot(observation: Observation, *, stale_seconds: int = 60) -> bytes:
    """Encode an observation as a CoT event. Observations without a position are rejected."""
    if observation.position is None:
        raise ValueError("cannot encode an observation without a position")
    position = observation.position
    has_hae = position.alt_m is not None and position.alt_ref is AltitudeReference.ELLIPSOID
    observed = observation.observed_at
    event = ET.Element(
        "event",
        {
            "version": "2.0",
            "uid": f"{observation.source_id}.{observation.entity_id}",
            "type": _COT_TYPES[observation.entity_type],
            "how": "m-g",
            "time": _cot_time(observed),
            "start": _cot_time(observed),
            "stale": _cot_time(observed + timedelta(seconds=stale_seconds)),
        },
    )
    accuracy = (
        f"{observation.position_accuracy_m:.1f}"
        if observation.position_accuracy_m is not None
        else _COT_UNKNOWN
    )
    ET.SubElement(
        event,
        "point",
        {
            "lat": f"{position.lat:.7f}",
            "lon": f"{position.lon:.7f}",
            "hae": f"{position.alt_m:.1f}" if has_hae else _COT_UNKNOWN,
            "ce": accuracy,
            "le": _COT_UNKNOWN,
        },
    )
    detail = ET.SubElement(event, "detail")
    if observation.velocity is not None:
        ET.SubElement(
            detail,
            "track",
            {
                "course": f"{observation.velocity.course_deg:.1f}",
                "speed": f"{observation.velocity.speed_mps:.2f}",
            },
        )
    encoded: bytes = ET.tostring(event, encoding="utf-8", xml_declaration=True)
    return encoded


def to_geojson_feature(observation: Observation) -> dict[str, Any]:
    """Encode an observation as a GeoJSON Feature (coordinates are lon, lat[, alt])."""
    geometry: dict[str, Any] | None = None
    if observation.position is not None:
        position = observation.position
        coordinates = [position.lon, position.lat]
        if position.alt_m is not None and position.alt_ref is AltitudeReference.ELLIPSOID:
            coordinates.append(position.alt_m)
        geometry = {"type": "Point", "coordinates": coordinates}
    properties: dict[str, Any] = {
        **observation.attributes,
        "id": str(observation.id),
        "source_id": observation.source_id,
        "entity_id": observation.entity_id,
        "entity_type": observation.entity_type.value,
        "observed_at": observation.observed_at.isoformat(),
    }
    if (
        observation.position is not None
        and observation.position.alt_m is not None
        and observation.position.alt_ref is AltitudeReference.MSL
    ):
        properties["alt_msl_m"] = observation.position.alt_m
    if observation.velocity is not None:
        properties["course_deg"] = observation.velocity.course_deg
        properties["speed_mps"] = observation.velocity.speed_mps
    return {"type": "Feature", "geometry": geometry, "properties": properties}


def to_geojson(observations: Iterable[Observation]) -> dict[str, Any]:
    """Encode observations as a FeatureCollection, skipping those without a position."""
    return {
        "type": "FeatureCollection",
        "features": [to_geojson_feature(o) for o in observations if o.position is not None],
    }
