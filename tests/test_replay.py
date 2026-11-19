import pytest

from tessera.encoders import to_cot
from tessera.eventlog import EventLog
from tessera.replay import Replayer


def _filled_log(tmp_path, make_observation, count=50):
    log = EventLog(tmp_path / "log.db")
    for i in range(count):
        log.append(make_observation(i))
    return log


def test_replay_is_deterministic(tmp_path, make_observation):
    with _filled_log(tmp_path, make_observation) as log:
        first = [to_cot(o) for o in Replayer(log, speed=0)]
        second = [to_cot(o) for o in Replayer(log, speed=0)]
    assert first == second
    assert len(first) == 50


def test_replay_delays_follow_recorded_time(tmp_path, make_observation):
    delays: list[float] = []
    with _filled_log(tmp_path, make_observation, count=4) as log:
        list(Replayer(log, speed=2.0, sleep=delays.append))
    assert delays == [0.5, 0.5, 0.5]


def test_speed_zero_never_sleeps(tmp_path, make_observation):
    delays: list[float] = []
    with _filled_log(tmp_path, make_observation, count=4) as log:
        list(Replayer(log, speed=0, sleep=delays.append))
    assert delays == []


def test_negative_speed_rejected(tmp_path, make_observation):
    with _filled_log(tmp_path, make_observation, count=1) as log, pytest.raises(ValueError):
        Replayer(log, speed=-1)
