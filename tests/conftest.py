from datetime import UTC, datetime, timedelta

import pytest

from tessera.models import EntityType, Observation, Position, Velocity

T0 = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def make_observation():
    def _make(index: int = 0, *, with_position: bool = True) -> Observation:
        moment = T0 + timedelta(seconds=index)
        return Observation(
            source_id="sitl-1",
            entity_id=f"uav-{index % 3}",
            entity_type=EntityType.UAV,
            observed_at=moment,
            ingested_at=moment,
            position=Position(lat=48.137 + index * 1e-4, lon=11.575, alt_m=520.0)
            if with_position
            else None,
            velocity=Velocity(course_deg=90.0, speed_mps=12.5),
            position_accuracy_m=2.5,
            attributes={"battery_pct": 87},
        )

    return _make
