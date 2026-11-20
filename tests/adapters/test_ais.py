from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pyais import decode as oracle_decode
from pyais.encode import encode_dict

from tessera.adapters.ais import MAX_CHUNK_BYTES, AisAdapter
from tessera.errors import AdapterError
from tessera.models import EntityType

NOW = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)
_KNOTS = 1852.0 / 3600.0


def sentence(**overrides) -> str:
    message = {
        "type": 1,
        "mmsi": "366053209",
        "lon": -122.4,
        "lat": 37.8,
        "speed": 12.3,
        "course": 45.6,
        "heading": 50,
        "status": 0,
    }
    message.update(overrides)
    return encode_dict(message, radio_channel="A")[0]


@pytest.fixture
def adapter() -> AisAdapter:
    return AisAdapter("ais-1", clock=lambda: NOW)


def test_matches_independent_decoder(adapter):
    raw = sentence()
    (obs,) = adapter.parse(raw.encode())
    reference = oracle_decode(raw).asdict()
    assert obs.entity_id == f"mmsi{reference['mmsi']}"
    assert obs.entity_type is EntityType.VESSEL
    assert obs.position.lat == pytest.approx(reference["lat"], abs=1e-5)
    assert obs.position.lon == pytest.approx(reference["lon"], abs=1e-5)
    assert obs.velocity.course_deg == pytest.approx(reference["course"], abs=0.05)
    assert obs.velocity.speed_mps == pytest.approx(reference["speed"] * _KNOTS, abs=0.01)


@pytest.mark.parametrize(
    ("lat", "lon"), [(0.0, 0.0), (-33.86, 151.2), (59.9, -179.9), (-89.9, 179.9), (51.5, -0.12)]
)
def test_positions_across_the_globe(adapter, lat, lon):
    (obs,) = adapter.parse(sentence(lat=lat, lon=lon).encode())
    assert obs.position.lat == pytest.approx(lat, abs=1e-5)
    assert obs.position.lon == pytest.approx(lon, abs=1e-5)


def test_multiple_lines_in_one_chunk(adapter):
    chunk = (sentence(mmsi="111111111") + "\r\n" + sentence(mmsi="222222222") + "\r\n").encode()
    assert [o.entity_id for o in adapter.parse(chunk)] == ["mmsi111111111", "mmsi222222222"]


def test_bad_checksum_dropped_and_counted(adapter):
    bad = sentence()[:-2] + "00"
    assert adapter.parse(bad.encode()) == []
    assert adapter.rejected == 1


def test_unavailable_position_rejected(adapter):
    assert adapter.parse(sentence(lat=91.0, lon=181.0).encode()) == []
    assert adapter.rejected == 1


def test_non_ascii_rejected(adapter):
    assert adapter.parse("!AIVDM,\xe9".encode("latin-1")) == []


def test_oversized_chunk_raises(adapter):
    with pytest.raises(AdapterError):
        adapter.parse(b"!" * (MAX_CHUNK_BYTES + 1))


@given(st.binary(max_size=1_024))
def test_random_bytes_never_crash(raw):
    assert isinstance(AisAdapter("fuzz", clock=lambda: NOW).parse(raw), list)
