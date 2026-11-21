import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tessera.adapters.mavlink import MavlinkAdapter
from tessera.geo import destination, haversine_m
from tessera.integrity import TRUST_THRESHOLD, cross_source_score, score_track
from tessera.models import EntityType, Observation, Position, Velocity

T0 = datetime(2026, 11, 21, 9, 0, tzinfo=UTC)
FIXTURE = Path(__file__).parent / "fixtures" / "sitl_global_position_int.bin"


def fix(t: float, lat: float, lon: float, *, speed=0.0, course=0.0, acc=3.0, kind=EntityType.UAV):
    return Observation(
        source_id="s",
        entity_id="e",
        entity_type=kind,
        observed_at=T0 + timedelta(seconds=t),
        ingested_at=T0 + timedelta(seconds=t),
        position=Position(lat=lat, lon=lon),
        velocity=Velocity(course_deg=course, speed_mps=speed),
        position_accuracy_m=acc,
    )


def test_haversine_one_degree_latitude():
    assert haversine_m(0, 0, 1, 0) == pytest.approx(111_195, rel=1e-3)


@given(
    st.floats(-80, 80),
    st.floats(-179, 179),
    st.floats(0, 359.9),
    st.floats(0, 50_000),
)
def test_destination_round_trips_distance(lat, lon, bearing, distance):
    lat2, lon2 = destination(lat, lon, bearing, distance)
    assert haversine_m(lat, lon, lat2, lon2) == pytest.approx(distance, abs=0.01, rel=1e-6)
    assert -180 <= lon2 <= 180


def test_consistent_moving_track_is_trusted():
    track = []
    lat, lon = 48.137, 11.575
    for t in range(30):
        track.append(fix(t, lat, lon, speed=10.0, course=90.0))
        lat, lon = destination(lat, lon, 90.0, 10.0)
    scores = score_track(track)
    assert all(s.trusted for s in scores)
    assert min(s.score for s in scores) == 1.0


def test_sudden_jump_flagged_then_recovers_when_track_returns():
    track = [fix(t, 48.137, 11.575) for t in range(10)]
    track.append(fix(10, 48.140, 11.575))  # 330 m jump in 1 s
    track += [fix(t, 48.137, 11.575) for t in range(11, 15)]
    scores = score_track(track)
    assert not scores[10].trusted
    assert set(scores[10].reasons) == {"speed_exceeds_limit", "inconsistent_with_motion"}
    assert all(s.trusted for s in scores[11:])


def test_persistent_spoof_keeps_failing_until_window_grows():
    track = [fix(t, 48.137, 11.575) for t in range(5)]
    track += [fix(t, 48.140, 11.575) for t in range(5, 12)]  # held 330 m offset
    scores = score_track(track)
    assert sum(not s.trusted for s in scores[5:]) >= 5


def test_sitl_capture_scores_clean():
    adapter = MavlinkAdapter("sitl")
    observations = adapter.parse(FIXTURE.read_bytes())
    timed = [
        o.model_copy(
            update={"observed_at": T0 + timedelta(milliseconds=int(o.attributes["time_boot_ms"]))}
        )
        for o in observations
    ]
    assert all(s.trusted for s in score_track(timed))


def test_sitl_capture_with_injected_spoof_is_flagged():
    observations = MavlinkAdapter("sitl").parse(FIXTURE.read_bytes())
    timed = []
    for i, o in enumerate(observations):
        o = o.model_copy(
            update={"observed_at": T0 + timedelta(milliseconds=int(o.attributes["time_boot_ms"]))}
        )
        if i == 20:
            o = o.model_copy(
                update={"position": Position(lat=o.position.lat + 0.01, lon=o.position.lon)}
            )
        timed.append(o)
    scores = score_track(timed)
    assert not scores[20].trusted
    assert sum(not s.trusted for s in scores) == 1


def test_non_increasing_time_reported():
    scores = score_track([fix(0, 48.0, 11.0), fix(0, 48.0, 11.0)])
    assert "non_increasing_time" in scores[1].reasons


def test_vessel_speed_limit_differs_from_uav():
    jump = destination(48.0, 11.0, 0.0, 45.0)
    uav = score_track([fix(0, 48.0, 11.0, acc=20), fix(1, *jump, acc=20)])
    ship = score_track(
        [
            fix(0, 48.0, 11.0, acc=20, kind=EntityType.VESSEL),
            fix(1, *jump, acc=20, kind=EntityType.VESSEL),
        ]
    )
    assert "speed_exceeds_limit" not in uav[1].reasons
    assert "speed_exceeds_limit" in ship[1].reasons


def test_cross_source_agreement():
    a = fix(0, 48.137, 11.575)
    near = fix(0.2, *destination(48.137, 11.575, 45, 4.0))
    far = fix(0.2, *destination(48.137, 11.575, 45, 400.0))
    assert cross_source_score(a, near) == 1.0
    assert cross_source_score(a, far) < TRUST_THRESHOLD
    assert cross_source_score(a, fix(5, 48.137, 11.575)) is None


def test_nan_and_infinity_rejected_everywhere():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Observation(
            source_id="s",
            entity_id="e",
            entity_type=EntityType.SENSOR,
            observed_at=T0,
            ingested_at=T0,
            attributes={"x": math.nan},
        )
    with pytest.raises(ValidationError):
        Velocity(course_deg=0.0, speed_mps=math.inf)
