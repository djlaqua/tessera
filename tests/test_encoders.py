import pytest
from defusedxml import ElementTree

from tessera.encoders import to_cot, to_geojson, to_geojson_feature


def test_cot_is_valid_and_has_expected_fields(make_observation):
    root = ElementTree.fromstring(to_cot(make_observation(0)))
    assert root.tag == "event"
    assert root.get("uid") == "sitl-1.uav-0"
    point = root.find("point")
    assert point is not None
    assert point.get("lat") == "48.1370000"
    assert root.find("detail/track").get("speed") == "12.50"


def test_cot_requires_position(make_observation):
    with pytest.raises(ValueError):
        to_cot(make_observation(0, with_position=False))


def test_cot_is_stable(make_observation):
    obs = make_observation(3)
    assert to_cot(obs) == to_cot(obs)


def test_geojson_uses_lon_lat_order(make_observation):
    feature = to_geojson_feature(make_observation(0))
    assert feature["geometry"]["coordinates"][:2] == [11.575, 48.137]


def test_geojson_core_properties_not_overridden_by_attributes(make_observation):
    obs = make_observation(0).model_copy(update={"attributes": {"id": "spoofed"}})
    assert to_geojson_feature(obs)["properties"]["id"] == str(obs.id)


def test_feature_collection_skips_positionless(make_observation):
    collection = to_geojson([make_observation(0), make_observation(1, with_position=False)])
    assert len(collection["features"]) == 1
