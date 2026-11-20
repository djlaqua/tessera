# Vision and Strategy

## Thesis
GNSS jamming and spoofing, fragmented sensor tooling, and unreliable links are now
permanent operating conditions. Operators need (1) one trustworthy spatial picture
from incompatible sources and (2) positions they can trust when GNSS cannot be.

## Product
**Phase 1: Spatial Stream & Replay Engine.** Edge daemon plus live map. Ingests MAVLink,
AIS, MQTT and GeoJSON, normalizes CRS and schema, stores an append-only log, replays
deterministically, outputs CoT and GeoJSON, syncs over degraded links with delta compression.

**Phase 2: Localization module.** Visual and DEM matching that emits a position fix with
covariance and an **integrity score** (trustworthy vs hallucinated). Plugs into the same engine.

## Wedge
Not "generic middleware". Initial wedge (confirm after discovery calls):
civil drone fleet telemetry plus local grid or environmental sensors, bridged to
TAK/GIS formats over weak cellular or radio, with a crisp live map and incident replay.

## Why the hybrid beats either option alone
- B alone: fast revenue, weaker technical moat, crowded with integrators.
- A alone: strong moat, 12 to 24+ months to revenue, hardware cost.
- Hybrid: B funds and instruments A. The replay engine becomes the test harness that
  validates A against recorded flights, which is the hardest part of A.

## Positioning
"The flight recorder and common picture that keeps working when the network and GNSS do not."

## Principles
Edge first, offline first, deterministic, open standards, small attack surface.
