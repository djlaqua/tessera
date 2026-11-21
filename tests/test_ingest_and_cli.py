import json
import socket
from datetime import UTC, datetime

from pymavlink.dialects.v20 import common as mavlink2

from tessera.adapters.mavlink import MavlinkAdapter
from tessera.cli import main
from tessera.errors import AdapterError
from tessera.eventlog import EventLog
from tessera.ingest import bind_udp, ingest_socket

NOW = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)


def _frame(sysid: int) -> bytes:
    tx = mavlink2.MAVLink(None, srcSystem=sysid, srcComponent=1)
    return bytes(
        tx.global_position_int_encode(1, 481_370_000, 115_750_000, 520_000, 0, 0, 0, 0, 0).pack(tx)
    )


def _send(port: int, payloads: list[bytes]) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        for payload in payloads:
            sender.sendto(payload, ("127.0.0.1", port))


def test_ingest_stores_until_max_events(tmp_path):
    with bind_udp("127.0.0.1", 0) as sock, EventLog(tmp_path / "log.db") as log:
        _send(sock.getsockname()[1], [_frame(1), _frame(2), _frame(3)])
        stored = ingest_socket(
            sock,
            log,
            MavlinkAdapter("t", clock=lambda: NOW),
            max_events=2,
            idle_timeout_s=2.0,
        )
        assert stored == 2
        assert log.count() == 2


def test_ingest_stops_when_idle(tmp_path):
    with bind_udp("127.0.0.1", 0) as sock, EventLog(tmp_path / "log.db") as log:
        stored = ingest_socket(sock, log, MavlinkAdapter("t"), idle_timeout_s=0.2)
        assert stored == 0


def test_ingest_survives_garbage(tmp_path):
    # 8,000 bytes stays under the macOS loopback datagram limit (about 9 KB).
    with bind_udp("127.0.0.1", 0) as sock, EventLog(tmp_path / "log.db") as log:
        _send(sock.getsockname()[1], [b"\x00" * 8_000, b"junk", _frame(1)])
        stored = ingest_socket(
            sock, log, MavlinkAdapter("t", clock=lambda: NOW), max_events=1, idle_timeout_s=2.0
        )
        assert stored == 1


class _RaisesOnce:
    """Adapter stub that rejects its first datagram, like an oversized chunk would be."""

    name = "stub"

    def __init__(self) -> None:
        self._inner = MavlinkAdapter("t", clock=lambda: NOW)
        self._calls = 0

    def parse(self, raw: bytes):
        self._calls += 1
        if self._calls == 1:
            raise AdapterError("too large")
        return self._inner.parse(raw)


def test_ingest_continues_after_adapter_error(tmp_path):
    with bind_udp("127.0.0.1", 0) as sock, EventLog(tmp_path / "log.db") as log:
        _send(sock.getsockname()[1], [b"first", _frame(1)])
        stored = ingest_socket(sock, log, _RaisesOnce(), max_events=1, idle_timeout_s=2.0)
        assert stored == 1


def test_cli_replay_geojson(tmp_path, capsys):
    db = tmp_path / "log.db"
    with bind_udp("127.0.0.1", 0) as sock, EventLog(db) as log:
        _send(sock.getsockname()[1], [_frame(1)])
        ingest_socket(
            sock, log, MavlinkAdapter("t", clock=lambda: NOW), max_events=1, idle_timeout_s=2.0
        )
    assert main(["replay", "--db", str(db), "--format", "geojson"]) == 0
    collection = json.loads(capsys.readouterr().out)
    feature = collection["features"][0]
    assert feature["geometry"]["coordinates"] == [11.575, 48.137]
    assert feature["properties"]["alt_msl_m"] == 520.0


def test_cli_replay_cot_omits_msl_height_as_hae(tmp_path, capsys):
    db = tmp_path / "log.db"
    with bind_udp("127.0.0.1", 0) as sock, EventLog(db) as log:
        _send(sock.getsockname()[1], [_frame(1)])
        ingest_socket(
            sock, log, MavlinkAdapter("t", clock=lambda: NOW), max_events=1, idle_timeout_s=2.0
        )
    assert main(["replay", "--db", str(db), "--format", "cot"]) == 0
    assert 'hae="9999999.0"' in capsys.readouterr().out
