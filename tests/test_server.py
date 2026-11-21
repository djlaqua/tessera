from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tessera.eventlog import EventLog
from tessera.models import EntityType, Observation, Position, Velocity
from tessera.server import MAX_SYNC_BODY_BYTES, create_app
from tessera.sync import Hub, HubStore, build_batch
from tessera.sync.signing import generate_private_key

T0 = datetime(2026, 11, 21, 9, 0, tzinfo=UTC)


def obs(i: int, *, lat: float | None = None) -> Observation:
    moment = T0 + timedelta(seconds=i)
    return Observation(
        source_id="edge",
        entity_id="uav-1",
        entity_type=EntityType.UAV,
        observed_at=moment,
        ingested_at=moment,
        position=Position(lat=lat if lat is not None else 48.137, lon=11.575),
        velocity=Velocity(course_deg=0.0, speed_mps=0.0),
        position_accuracy_m=2.0,
    )


@pytest.fixture
def key():
    return generate_private_key()


@pytest.fixture
def hub_client(tmp_path, key):
    hub = Hub(HubStore(tmp_path / "hub.db"), {"edge-1": key.public_key()})
    return TestClient(create_app(tmp_path / "hub.db", hub=hub))


def test_security_headers_and_no_docs(hub_client):
    response = hub_client.get("/healthz")
    assert response.json() == {"status": "ok", "mode": "hub"}
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert "https://tile.openstreetmap.org" in csp
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "server" not in response.headers or "uvicorn" not in response.headers["server"]
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert hub_client.get(path).status_code == 404


def test_sync_then_features(hub_client, key):
    batch = build_batch("edge-1", [(i + 1, obs(i)) for i in range(5)], key)
    response = hub_client.post("/v1/sync", content=batch.model_dump_json())
    assert response.status_code == 200
    assert response.json() == {"edge_id": "edge-1", "acked_seq": 5}
    collection = hub_client.get("/v1/features").json()
    (feature,) = collection["features"]
    props = feature["properties"]
    assert props["entity_id"] == "uav-1"
    assert len(props["trail"]) == 5
    assert props["integrity"] == 1.0
    assert props["flagged_in_window"] == 0


def test_spoofed_jump_is_flagged_on_the_map(hub_client, key):
    rows = [(i + 1, obs(i)) for i in range(5)]
    rows.append((6, obs(5, lat=48.147)))  # about 1.1 km jump in 1 s
    hub_client.post("/v1/sync", content=build_batch("edge-1", rows, key).model_dump_json())
    props = hub_client.get("/v1/features").json()["features"][0]["properties"]
    assert props["integrity"] < 0.5
    assert "speed_exceeds_limit" in props["integrity_reasons"]
    assert props["flagged_in_window"] == 1


def test_sync_rejects_bad_signature_with_generic_401(hub_client):
    batch = build_batch("edge-1", [(1, obs(0))], generate_private_key())
    response = hub_client.post("/v1/sync", content=batch.model_dump_json())
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_sync_rejects_malformed_and_oversized(hub_client):
    assert hub_client.post("/v1/sync", content=b"{not json").status_code == 400
    big = b"x" * (MAX_SYNC_BODY_BYTES + 1)
    assert hub_client.post("/v1/sync", content=big).status_code == 413


def test_edge_mode_has_no_sync_endpoint(tmp_path):
    with EventLog(tmp_path / "edge.db") as log:
        log.append(obs(0))
    client = TestClient(create_app(tmp_path / "edge.db"))
    assert client.get("/healthz").json()["mode"] == "edge"
    assert client.post("/v1/sync", content=b"{}").status_code in (404, 405)
    assert len(client.get("/v1/features").json()["features"]) == 1


def test_read_token_required_when_configured(tmp_path):
    client = TestClient(create_app(tmp_path / "missing.db", read_token="s3cret"))
    assert client.get("/v1/features").status_code == 401
    assert client.get("/v1/features", headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = client.get("/v1/features", headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200 and ok.json()["features"] == []
    assert client.get("/v1/config").json()["auth_required"] is True


def test_query_limits_enforced(hub_client):
    assert hub_client.get("/v1/features?window=0").status_code == 422
    assert hub_client.get("/v1/features?trail=100000").status_code == 422


def test_map_page_and_vendored_assets(hub_client):
    page = hub_client.get("/")
    assert page.status_code == 200 and "Tessera Live" in page.text
    assert "unpkg" not in page.text and "cdn" not in page.text
    for asset in ("/static/app.js", "/static/app.css", "/static/vendor/leaflet/leaflet.js"):
        assert hub_client.get(asset).status_code == 200


def test_http_tile_url_not_allowed_in_csp(tmp_path):
    client = TestClient(
        create_app(tmp_path / "x.db", tile_url="http://evil.example/{z}/{x}/{y}.png")
    )
    assert "evil.example" not in client.get("/healthz").headers["content-security-policy"]


def _platform_obs(i, entity, source_kind, lat):
    o = obs(i, lat=lat)
    return o.model_copy(
        update={
            "entity_id": entity,
            "attributes": {"platform": "uav-1", "position_source": source_kind},
        }
    )


def test_cross_source_disagreement_flags_spoofed_gps(hub_client, key):
    rows = []
    seq = 0
    for i in range(5):
        seq += 1
        rows.append((seq, _platform_obs(i, "uav-1", "fused", 48.137)))
        seq += 1
        rows.append((seq, _platform_obs(i, "uav-1.gps1", "gps1", 48.137 + i * 0.002)))  # walk-off
    hub_client.post("/v1/sync", content=build_batch("edge-1", rows, key).model_dump_json())
    features = {
        f["properties"]["entity_id"]: f["properties"]
        for f in hub_client.get("/v1/features").json()["features"]
    }
    assert features["uav-1.gps1"]["cross_source"] < 0.5
    assert "sources_disagree" in features["uav-1.gps1"]["integrity_reasons"]
    assert features["uav-1"]["cross_source"] < 0.5
