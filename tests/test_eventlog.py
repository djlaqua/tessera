import sqlite3

import pytest

from tessera.errors import LogCorruptionError
from tessera.eventlog import EventLog


def test_append_and_read_in_order(tmp_path, make_observation):
    with EventLog(tmp_path / "log.db") as log:
        seqs = [log.append(make_observation(i)) for i in range(5)]
        assert seqs == sorted(seqs)
        assert log.count() == 5
        expected = [make_observation(i).entity_id for i in range(5)]
        assert [o.entity_id for _, o in log.read()] == expected


def test_survives_reopen(tmp_path, make_observation):
    path = tmp_path / "log.db"
    with EventLog(path) as log:
        log.append(make_observation(1))
    with EventLog(path) as log:
        assert log.count() == 1


def test_read_after_sequence(tmp_path, make_observation):
    with EventLog(tmp_path / "log.db") as log:
        first = log.append(make_observation(0))
        log.append(make_observation(1))
        assert len(list(log.read(after_seq=first))) == 1


def test_corrupt_row_fails_loudly(tmp_path, make_observation):
    path = tmp_path / "log.db"
    with EventLog(path) as log:
        log.append(make_observation(0))
    conn = sqlite3.connect(path)
    conn.execute("UPDATE events SET payload = '{\"broken\": true}'")
    conn.commit()
    conn.close()
    with EventLog(path) as log, pytest.raises(LogCorruptionError):
        list(log.read())
