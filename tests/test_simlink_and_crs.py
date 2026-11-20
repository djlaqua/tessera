import socket
from datetime import UTC, datetime

import pytest
from pymavlink.dialects.v20 import common as mavlink2

from tessera.adapters.mavlink import MavlinkAdapter
from tessera.crs import from_wgs84, to_wgs84
from tessera.eventlog import EventLog
from tessera.ingest import bind_udp, ingest_socket
from tessera.simlink import degrade

NOW = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)


def test_degrade_is_deterministic():
    packets = [bytes([i]) for i in range(100)]
    kwargs = {"loss": 0.2, "duplicate": 0.1, "reorder": 0.2, "jitter_s": 0.05, "seed": 7}
    assert degrade(packets, **kwargs) == degrade(packets, **kwargs)


def test_degrade_loss_bounds():
    packets = [bytes([i]) for i in range(50)]
    assert len(degrade(packets, loss=0.0)) == 50
    assert degrade(packets, loss=1.0) == []


def test_degrade_rejects_bad_probability():
    with pytest.raises(ValueError):
        degrade([b"x"], loss=1.5)


def test_ingest_through_degraded_link_keeps_ingest_order(tmp_path):
    tx = mavlink2.MAVLink(None, srcSystem=1, srcComponent=1)
    frames = [
        bytes(
            tx.global_position_int_encode(i, 481_370_000 + i, 115_750_000, 0, 0, 0, 0, 0, 0).pack(
                tx
            )
        )
        for i in range(60)
    ]
    degraded = degrade(frames, loss=0.2, duplicate=0.1, reorder=0.3, seed=3)
    with bind_udp("127.0.0.1", 0) as sock, EventLog(tmp_path / "log.db") as log:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            for packet in degraded:
                sender.sendto(packet.payload, sock.getsockname())
        stored = ingest_socket(
            sock, log, MavlinkAdapter("t", clock=lambda: NOW), idle_timeout_s=0.5
        )
        seqs = [seq for seq, _ in log.read()]
    assert stored == len(degraded)
    assert seqs == sorted(seqs) == list(range(1, stored + 1))


def test_utm32n_central_meridian_is_9_degrees_east():
    lat, lon = to_wgs84(500_000.0, 0.0, 25832)
    assert lat == pytest.approx(0.0, abs=1e-9)
    assert lon == pytest.approx(9.0, abs=1e-9)


def test_round_trip_within_one_centimeter():
    lat, lon = 48.1374, 11.5755
    x, y = from_wgs84(lat, lon, 25832)
    back_lat, back_lon = to_wgs84(x, y, 25832)
    assert abs(back_lat - lat) * 111_000 < 0.01
    assert abs(back_lon - lon) * 74_000 < 0.01


def test_axis_order_is_x_then_y():
    lat, lon = to_wgs84(691_000.0, 5_335_000.0, 25832)
    assert 47.0 < lat < 49.0
    assert 11.0 < lon < 12.5
