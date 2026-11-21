import json
import stat
from datetime import UTC, datetime, timedelta

from tessera.cli import main
from tessera.eventlog import EventLog
from tessera.models import EntityType, Observation, Position

T0 = datetime(2026, 11, 21, 9, 0, tzinfo=UTC)


def _obs(t, lat):
    return Observation(
        source_id="s",
        entity_id="e",
        entity_type=EntityType.UAV,
        observed_at=T0 + timedelta(seconds=t),
        ingested_at=T0 + timedelta(seconds=t),
        position=Position(lat=lat, lon=11.575),
        position_accuracy_m=2.0,
    )


def test_keygen_creates_private_and_public_keys(tmp_path):
    out = tmp_path / "edge-1.key"
    assert main(["keygen", "--out", str(out)]) == 0
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    assert (tmp_path / "edge-1.key.pub").read_text().startswith("-----BEGIN PUBLIC KEY-----")


def test_integrity_command_reports_flagged_fixes(tmp_path, capsys):
    db = tmp_path / "log.db"
    with EventLog(db) as log:
        for t in range(5):
            log.append(_obs(t, 48.137))
        log.append(_obs(5, 48.147))
    assert main(["integrity", "--db", str(db)]) == 0
    captured = capsys.readouterr()
    assert "scored 6 fixes, flagged 1" in captured.err
    (line,) = captured.out.strip().splitlines()
    assert json.loads(line)["reasons"] == ["speed_exceeds_limit", "inconsistent_with_motion"]


def test_replay_geojson_streams_valid_json(tmp_path, capsys):
    db = tmp_path / "log.db"
    with EventLog(db) as log:
        for t in range(3):
            log.append(_obs(t, 48.137))
    assert main(["replay", "--db", str(db)]) == 0
    assert len(json.loads(capsys.readouterr().out)["features"]) == 3


def test_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip()
