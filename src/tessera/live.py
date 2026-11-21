"""Live picture: newest position, trail and integrity per entity, from any event store."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tessera.encoders import to_geojson_feature
from tessera.integrity import TRUST_THRESHOLD, cross_source_score, score_track
from tessera.models import Observation

MAX_WINDOW = 20_000
MAX_TRAIL = 500


def recent_observations(db_path: str | Path, window: int) -> tuple[list[Observation], int]:
    """Read the newest `window` events, read-only. Returns (observations, skipped_rows)."""
    window = max(1, min(window, MAX_WINDOW))
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        rows = conn.execute(
            "SELECT payload FROM events ORDER BY ingest_seq DESC LIMIT ?", (window,)
        ).fetchall()
    finally:
        conn.close()
    observations: list[Observation] = []
    skipped = 0
    for (payload,) in rows:
        try:
            observations.append(Observation.model_validate_json(payload))
        except ValidationError:
            skipped += 1
    return observations, skipped


def live_features(db_path: str | Path, *, window: int = 2_000, trail: int = 50) -> dict[str, Any]:
    """FeatureCollection with one Point per entity: newest fix, trail and integrity."""
    trail = max(0, min(trail, MAX_TRAIL))
    observations, skipped = recent_observations(db_path, window)
    tracks: dict[tuple[str, str], list[Observation]] = defaultdict(list)
    for observation in observations:
        if observation.position is not None:
            tracks[(observation.source_id, observation.entity_id)].append(observation)
    latest_by_platform: dict[tuple[str, str], list[Observation]] = defaultdict(list)
    for track in tracks.values():
        newest = max(track, key=lambda o: o.observed_at)
        platform = newest.attributes.get("platform")
        if isinstance(platform, str):
            latest_by_platform[(newest.source_id, platform)].append(newest)
    cross: dict[tuple[str, str], float] = {}
    for fixes in latest_by_platform.values():
        for a in fixes:
            for b in fixes:
                if a is b:
                    continue
                score = cross_source_score(a, b, max_dt_s=2.0)
                if score is not None:
                    key = (a.source_id, a.entity_id)
                    cross[key] = min(cross.get(key, 1.0), score)
    features: list[dict[str, Any]] = []
    for track in tracks.values():
        track.sort(key=lambda o: o.observed_at)
        scores = score_track(track)
        feature = to_geojson_feature(track[-1])
        feature["properties"].update(
            {
                "trail": [
                    [o.position.lon, o.position.lat]
                    for o in track[len(track) - trail :]
                    if o.position is not None
                ],
                "integrity": scores[-1].score,
                "integrity_reasons": list(scores[-1].reasons),
                "flagged_in_window": sum(1 for s in scores if not s.trusted),
                "fixes_in_window": len(track),
            }
        )
        agreement = cross.get((track[-1].source_id, track[-1].entity_id))
        if agreement is not None:
            feature["properties"]["cross_source"] = agreement
            if agreement < TRUST_THRESHOLD:
                feature["properties"]["integrity"] = min(
                    feature["properties"]["integrity"], agreement
                )
                feature["properties"]["integrity_reasons"].append("sources_disagree")
        features.append(feature)
    features.sort(
        key=lambda f: (str(f["properties"]["source_id"]), str(f["properties"]["entity_id"]))
    )
    return {"type": "FeatureCollection", "features": features, "skipped_rows": skipped}
