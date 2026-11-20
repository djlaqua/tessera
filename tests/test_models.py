from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from tessera.models import EntityType, Observation, Position


def _base(**overrides):
    values = {
        "source_id": "s1",
        "entity_id": "e1",
        "entity_type": EntityType.UAV,
        "observed_at": datetime(2026, 1, 1, tzinfo=UTC),
        "ingested_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(("lat", "lon"), [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_position_out_of_range_rejected(lat, lon):
    with pytest.raises(ValidationError):
        Position(lat=lat, lon=lon)


def test_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        Observation(**_base(observed_at=datetime(2026, 1, 1)))


def test_timestamps_normalized_to_utc():
    plus_two = timezone(timedelta(hours=2))
    obs = Observation(**_base(observed_at=datetime(2026, 1, 1, 2, tzinfo=plus_two)))
    assert obs.observed_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert obs.observed_at.utcoffset() == timedelta(0)


def test_identifier_rejects_unsafe_characters():
    with pytest.raises(ValidationError):
        Observation(**_base(entity_id="bad id<script>"))


def test_attribute_count_bounded():
    with pytest.raises(ValidationError):
        Observation(**_base(attributes={f"k{i}": i for i in range(33)}))


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Observation(**_base(unexpected=1))


def test_observation_is_immutable():
    obs = Observation(**_base())
    with pytest.raises(ValidationError):
        obs.source_id = "other"
