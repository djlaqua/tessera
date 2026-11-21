import base64
import json
import zlib
from datetime import UTC, datetime, timedelta

import pytest

from tessera.eventlog import EventLog
from tessera.models import EntityType, Observation, Position
from tessera.sync import Ack, Hub, HubStore, SyncBatch, Uplink, build_batch, open_batch
from tessera.sync.batch import MAX_BATCH_EVENTS
from tessera.sync.errors import AuthError, SyncError, TransportError
from tessera.sync.http import HttpTransport
from tessera.sync.signing import (
    generate_private_key,
    load_private_key,
    save_private_key,
)

T0 = datetime(2026, 11, 21, 9, 0, tzinfo=UTC)


def obs(i: int) -> Observation:
    moment = T0 + timedelta(seconds=i)
    return Observation(
        source_id="edge",
        entity_id="uav-1",
        entity_type=EntityType.UAV,
        observed_at=moment,
        ingested_at=moment,
        position=Position(lat=48.137 + i * 1e-5, lon=11.575),
    )


@pytest.fixture
def key():
    return generate_private_key()


@pytest.fixture
def hub(tmp_path, key):
    return Hub(HubStore(tmp_path / "hub.db"), {"edge-1": key.public_key()})


class Direct:
    """In-process transport that can simulate an outage."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.down = False
        self.calls = 0

    def send(self, batch: SyncBatch) -> Ack:
        self.calls += 1
        if self.down:
            raise TransportError("link down")
        return self.hub.receive(batch)


def fill(log: EventLog, n: int) -> None:
    for i in range(n):
        log.append(obs(i))


def test_round_trip(key):
    rows = [(i + 1, obs(i)) for i in range(10)]
    batch = build_batch("edge-1", rows, key)
    assert open_batch(batch) == rows


def test_drain_delivers_everything_in_batches(tmp_path, key, hub):
    transport = Direct(hub)
    with EventLog(tmp_path / "edge.db") as log:
        fill(log, 25)
        uplink = Uplink(
            log, peer="hub", edge_id="edge-1", key=key, transport=transport, max_events=10
        )
        assert uplink.drain() == 25
        assert log.get_cursor("hub") == 25
        assert transport.calls == 3
        assert uplink.drain() == 0
    assert hub.store.count() == 25


def test_store_and_forward_survives_outage(tmp_path, key, hub):
    transport = Direct(hub)
    with EventLog(tmp_path / "edge.db") as log:
        fill(log, 5)
        uplink = Uplink(log, peer="hub", edge_id="edge-1", key=key, transport=transport)
        transport.down = True
        with pytest.raises(TransportError):
            uplink.drain()
        assert log.get_cursor("hub") == 0
        transport.down = False
        assert uplink.drain() == 5
    assert hub.store.count() == 5


def test_duplicate_batch_is_idempotent(key, hub):
    batch = build_batch("edge-1", [(i + 1, obs(i)) for i in range(3)], key)
    assert hub.receive(batch).acked_seq == 3
    assert hub.receive(batch).acked_seq == 3
    assert hub.store.count() == 3


def test_gap_makes_edge_rewind_and_resend(tmp_path, key, hub):
    transport = Direct(hub)
    with EventLog(tmp_path / "edge.db") as log:
        fill(log, 6)
        log.set_cursor("hub", 4)  # edge believes the hub has 1..4 (for example hub restored)
        uplink = Uplink(log, peer="hub", edge_id="edge-1", key=key, transport=transport)
        uplink.drain()
        assert log.get_cursor("hub") == 6
    assert hub.store.count() == 6


def test_unknown_edge_rejected(key, hub):
    batch = build_batch("stranger", [(1, obs(0))], key)
    with pytest.raises(AuthError):
        hub.receive(batch)


def test_wrong_key_rejected(hub):
    batch = build_batch("edge-1", [(1, obs(0))], generate_private_key())
    with pytest.raises(AuthError):
        hub.receive(batch)


def test_tampered_header_rejected(key, hub):
    batch = build_batch("edge-1", [(1, obs(0)), (2, obs(1))], key)
    tampered = batch.model_copy(update={"first_seq": 2, "count": 1})
    with pytest.raises(AuthError):
        hub.receive(tampered)


def test_tampered_payload_rejected(key):
    batch = build_batch("edge-1", [(1, obs(0))], key)
    raw = bytearray(base64.b64decode(batch.payload_b64))
    raw[-1] ^= 0xFF
    tampered = batch.model_copy(update={"payload_b64": base64.b64encode(bytes(raw)).decode()})
    with pytest.raises(SyncError):
        open_batch(tampered)


def _forge(key, rows_text: bytes, first: int, last: int, count: int) -> SyncBatch:
    import hashlib

    from tessera.sync.batch import signing_message
    from tessera.sync.signing import sign

    payload = zlib.compress(rows_text)
    digest = hashlib.sha256(payload).hexdigest()
    return SyncBatch(
        edge_id="edge-1",
        first_seq=first,
        last_seq=last,
        count=count,
        sha256=digest,
        payload_b64=base64.b64encode(payload).decode(),
        signature_b64=base64.b64encode(
            sign(key, signing_message("edge-1", first, last, count, digest))
        ).decode(),
    )


def test_decompression_bomb_rejected(key, hub):
    bomb = _forge(key, b"1\t" + b"A" * (9 * 1024 * 1024), 1, 1, 1)
    with pytest.raises(SyncError):
        hub.receive(bomb)


def test_out_of_order_rows_rejected(key, hub):
    body = f"2\t{obs(1).model_dump_json()}\n1\t{obs(0).model_dump_json()}".encode()
    with pytest.raises(SyncError):
        hub.receive(_forge(key, body, 1, 2, 2))


def test_batch_size_limit(key):
    rows = [(i + 1, obs(i)) for i in range(MAX_BATCH_EVENTS + 1)]
    with pytest.raises(SyncError):
        build_batch("edge-1", rows, key)


def test_ack_for_other_edge_rejected(tmp_path, key):
    class Liar:
        def send(self, batch):
            return Ack(edge_id="other", acked_seq=1)

    with EventLog(tmp_path / "edge.db") as log:
        fill(log, 1)
        with pytest.raises(SyncError):
            Uplink(log, peer="hub", edge_id="edge-1", key=key, transport=Liar()).run_once()


def test_run_backs_off_on_outage(tmp_path, key, hub):
    transport = Direct(hub)
    transport.down = True
    delays: list[float] = []
    with EventLog(tmp_path / "edge.db") as log:
        fill(log, 1)
        uplink = Uplink(log, peer="hub", edge_id="edge-1", key=key, transport=transport)
        uplink.run(
            interval_s=1.0,
            max_backoff_s=8.0,
            sleep=delays.append,
            should_stop=lambda: len(delays) >= 5,
        )
    assert delays == [2.0, 4.0, 8.0, 8.0, 8.0]


def test_private_key_permissions_enforced(tmp_path, key):
    path = tmp_path / "edge.key"
    save_private_key(key, path)
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    load_private_key(path)
    path.chmod(0o644)
    with pytest.raises(SyncError):
        load_private_key(path)


def test_private_key_never_overwritten(tmp_path, key):
    path = tmp_path / "edge.key"
    save_private_key(key, path)
    with pytest.raises(FileExistsError):
        save_private_key(key, path)


@pytest.mark.parametrize(
    "url", ["http://hub.example.com", "ftp://hub.example.com", "file:///etc/passwd", "hub"]
)
def test_http_transport_refuses_unsafe_urls(url):
    with pytest.raises(ValueError):
        HttpTransport(url)


def test_http_transport_allows_loopback_and_https():
    HttpTransport("http://127.0.0.1:8080")
    HttpTransport("https://hub.example.com")
    HttpTransport("http://hub:8080", allow_insecure_http=True)


def test_http_transport_unreachable_is_transport_error(key):
    transport = HttpTransport("http://127.0.0.1:9", timeout_s=1.0)
    with pytest.raises(TransportError):
        transport.send(build_batch("edge-1", [(1, obs(0))], key))


def test_ack_json_shape():
    assert json.loads(Ack(edge_id="e", acked_seq=3).model_dump_json()) == {
        "edge_id": "e",
        "acked_seq": 3,
    }
