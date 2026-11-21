"""Position integrity scoring, version 0 (heuristic; not certified for navigation).

Each fix gets a score in [0, 1] from two checks against the last trusted fix:
- kinematic: implied speed must not exceed a per entity type limit;
- motion consistency: the fix must agree with a constant velocity prediction within
  3 sigma, where sigma combines reported accuracy and process noise over the time gap.

Fixes scoring below `TRUST_THRESHOLD` do not become the new reference, so a sudden spoofed
jump keeps failing until the uncertainty window grows to contain it. A slow walk-off is not
detectable from one source; compare against an independent source with `cross_source_score`
(see ADR-011).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from tessera.geo import destination, haversine_m
from tessera.models import EntityType, Observation, Position

TRUST_THRESHOLD = 0.5
DEFAULT_ACCURACY_M = 5.0
PROCESS_NOISE_MPS = 3.0
GATE_SIGMA = 3.0
MAX_SPEED_MPS: dict[EntityType, float] = {
    EntityType.UAV: 60.0,
    EntityType.VESSEL: 30.0,
    EntityType.GROUND: 50.0,
    EntityType.SENSOR: 2.0,
}


@dataclass(frozen=True)
class FixScore:
    observation_id: UUID
    score: float
    reasons: tuple[str, ...]

    @property
    def trusted(self) -> bool:
        return self.score >= TRUST_THRESHOLD


def _accuracy(observation: Observation) -> float:
    return observation.position_accuracy_m or DEFAULT_ACCURACY_M


def _gate(error_m: float, sigma_m: float) -> float:
    z = error_m / sigma_m
    return 1.0 if z <= GATE_SIGMA else math.exp(-(z - GATE_SIGMA) / 2.0)


def _score_against(
    reference: Observation, ref_pos: Position, fix: Observation, pos: Position
) -> FixScore:
    dt = (fix.observed_at - reference.observed_at).total_seconds()
    reasons: list[str] = []
    kinematic = 1.0
    if dt > 0:
        limit = MAX_SPEED_MPS[fix.entity_type]
        implied = haversine_m(ref_pos.lat, ref_pos.lon, pos.lat, pos.lon) / dt
        if implied > limit:
            kinematic = math.exp(-(implied / limit - 1.0) * 2.0)
            reasons.append("speed_exceeds_limit")
    else:
        reasons.append("non_increasing_time")
    predicted = (ref_pos.lat, ref_pos.lon)
    if reference.velocity is not None and dt > 0:
        predicted = destination(
            ref_pos.lat,
            ref_pos.lon,
            reference.velocity.course_deg,
            reference.velocity.speed_mps * dt,
        )
    error = haversine_m(predicted[0], predicted[1], pos.lat, pos.lon)
    sigma = math.hypot(_accuracy(reference), _accuracy(fix), PROCESS_NOISE_MPS * max(dt, 0.0))
    motion = _gate(error, sigma)
    if motion < 1.0:
        reasons.append("inconsistent_with_motion")
    return FixScore(fix.id, round(min(kinematic, motion), 4), tuple(reasons))


def score_track(observations: Sequence[Observation]) -> list[FixScore]:
    """Score every positioned fix of one entity, in `observed_at` order."""
    fixes = sorted((o for o in observations if o.position is not None), key=lambda o: o.observed_at)
    results: list[FixScore] = []
    reference: tuple[Observation, Position] | None = None
    for fix in fixes:
        position = fix.position
        if position is None:  # narrowed for the type checker; filtered above
            continue
        if reference is None:
            result = FixScore(fix.id, 1.0, ("first_fix",))
        else:
            result = _score_against(reference[0], reference[1], fix, position)
        results.append(result)
        if result.trusted:
            reference = (fix, position)
    return results


def cross_source_score(a: Observation, b: Observation, *, max_dt_s: float = 1.0) -> float | None:
    """Agreement between two sources for the same entity, or None if not comparable."""
    if a.position is None or b.position is None:
        return None
    dt = abs((a.observed_at - b.observed_at).total_seconds())
    if dt > max_dt_s:
        return None
    error = haversine_m(a.position.lat, a.position.lon, b.position.lat, b.position.lon)
    sigma = math.hypot(_accuracy(a), _accuracy(b), PROCESS_NOISE_MPS * dt)
    return round(_gate(error, sigma), 4)
