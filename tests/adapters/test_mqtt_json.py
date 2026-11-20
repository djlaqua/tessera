import json
from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tessera.adapters.mqtt_json import MAX_PAYLOAD_BYTES, MqttJsonAdapter
from tessera.errors import AdapterError
from tessera.models import EntityType

NOW = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)


def payload(**overrides) -> bytes:
    body = {"entity_id": "pump-3", "lat": 48.1, "lon": 11.5, "attributes": {"battery_pct": 87}}
    body.update(overrides)
    return json.dumps(body).encode()


@pytest.fixture
def adapter() -> MqttJsonAdapter:
    return MqttJsonAdapter("mqtt-1", clock=lambda: NOW)


def test_valid_payload(adapter):
    (obs,) = adapter.parse(payload(alt_m=520.0, accuracy_m=3.0))
    assert obs.entity_id == "pump-3"
    assert obs.entity_type is EntityType.SENSOR
    assert obs.position.alt_m == 520.0
    assert obs.position_accuracy_m == 3.0
    assert obs.observed_at == NOW
    assert obs.attributes == {"battery_pct": 87}


def test_source_time_is_used(adapter):
    (obs,) = adapter.parse(payload(time="2026-11-20T08:59:00Z"))
    assert obs.observed_at == datetime(2026, 11, 20, 8, 59, tzinfo=UTC)
    assert obs.ingested_at == NOW


@pytest.mark.parametrize(
    "raw",
    [
        b"not json",
        b"[]",
        payload(lat=95),
        payload(entity_id="bad id!"),
        payload(unexpected=1),
        payload(time="2026-11-20T09:00:00"),  # naive time
        payload(attributes={"k": {"nested": 1}}),
    ],
)
def test_invalid_payloads_dropped_and_counted(adapter, raw):
    assert adapter.parse(raw) == []
    assert adapter.rejected == 1


def test_oversized_payload_raises(adapter):
    with pytest.raises(AdapterError):
        adapter.parse(b" " * (MAX_PAYLOAD_BYTES + 1))


@given(st.binary(max_size=1_024))
def test_random_bytes_never_crash(raw):
    assert isinstance(MqttJsonAdapter("fuzz", clock=lambda: NOW).parse(raw), list)
