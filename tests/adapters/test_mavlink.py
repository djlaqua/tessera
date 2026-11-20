from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pymavlink.dialects.v20 import common as mavlink2

from tessera.adapters.mavlink import MAX_CHUNK_BYTES, MavlinkAdapter
from tessera.errors import AdapterError
from tessera.models import AltitudeReference

NOW = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)


def frame(
    *,
    sysid: int = 7,
    lat: int = 481_370_000,
    lon: int = 115_750_000,
    alt: int = 520_000,
    vx: int = 300,
    vy: int = 400,
    hdg: int = 9_000,
) -> bytes:
    tx = mavlink2.MAVLink(None, srcSystem=sysid, srcComponent=1)
    message = tx.global_position_int_encode(1234, lat, lon, alt, 50_000, vx, vy, 5, hdg)
    return bytes(message.pack(tx))


@pytest.fixture
def adapter() -> MavlinkAdapter:
    return MavlinkAdapter("sitl-1", clock=lambda: NOW)


def test_parses_position_and_units(adapter):
    (obs,) = adapter.parse(frame())
    assert obs.entity_id == "sys7.comp1"
    assert obs.position.lat == pytest.approx(48.137)
    assert obs.position.lon == pytest.approx(11.575)
    assert obs.position.alt_m == pytest.approx(520.0)
    assert obs.position.alt_ref is AltitudeReference.MSL
    assert obs.observed_at == NOW
    assert obs.attributes["time_boot_ms"] == 1234
    assert obs.attributes["heading_deg"] == 90.0


def test_velocity_from_north_east_components(adapter):
    (obs,) = adapter.parse(frame(vx=300, vy=400))
    assert obs.velocity.speed_mps == pytest.approx(5.0)
    assert obs.velocity.course_deg == pytest.approx(53.130, abs=1e-3)


def test_negative_east_component_wraps_course(adapter):
    (obs,) = adapter.parse(frame(vx=0, vy=-100))
    assert obs.velocity.course_deg == pytest.approx(270.0)


def test_unknown_heading_omitted(adapter):
    (obs,) = adapter.parse(frame(hdg=65_535))
    assert "heading_deg" not in obs.attributes


def test_frame_split_across_chunks(adapter):
    data = frame()
    assert adapter.parse(data[:10]) == []
    assert len(adapter.parse(data[10:])) == 1


def test_multiple_frames_in_one_datagram(adapter):
    assert len(adapter.parse(frame(sysid=1) + frame(sysid=2))) == 2


def test_no_fix_is_counted_and_skipped(adapter):
    assert adapter.parse(frame(lat=0, lon=0)) == []
    assert adapter.rejected == 1


def test_out_of_range_latitude_rejected(adapter):
    assert adapter.parse(frame(lat=950_000_000)) == []
    assert adapter.rejected == 1


def test_oversized_chunk_raises(adapter):
    with pytest.raises(AdapterError):
        adapter.parse(b"\x00" * (MAX_CHUNK_BYTES + 1))


def test_corrupted_crc_dropped(adapter):
    data = bytearray(frame())
    data[-1] ^= 0xFF
    assert adapter.parse(bytes(data)) == []


@given(st.binary(max_size=2_048))
def test_random_bytes_never_crash(raw):
    adapter = MavlinkAdapter("fuzz", clock=lambda: NOW)
    assert isinstance(adapter.parse(raw), list)
