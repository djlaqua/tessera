# Vision and Strategy

## Thesis
GNSS jamming and spoofing, fragmented sensor tooling, and unreliable links are now
routine operating conditions (VERIFY with sourced incident data, research item R9).
Operators need (1) one picture from incompatible sources and (2) to know which positions
in that picture they can trust.

## Product
**Phase 1 (built): telemetry engine with integrity.** Edge daemon plus hub. Ingests
MAVLink, AIS and JSON telemetry, normalizes, stores an append-only log, replays
deterministically, outputs CoT and GeoJSON, and syncs signed batches over bad links to a
hub with a live map. Every track carries an integrity score; raw GNSS is compared with
the autopilot's fused estimate so a spoof or glitch shows up as disagreement.

**Phase 2 (next R&D): independent position sources.** Visual and DEM matching that emits a
position fix with covariance. Its first job is not to fly the vehicle but to act as an
independent witness for the integrity layer, which keeps scope and certification burden low.

## Wedge
Lead with the question operators already ask after an incident: "was that position real?"
Sharp offer: a fleet picture and flight recorder that flags untrustworthy positions, for
civil drone and vessel operators who already see GNSS interference. Middleware is the
carrier, integrity is the reason to buy. Confirm the segment through discovery calls.

## Why this order
- Middleware alone: fast to build, weak moat, crowded with integrators.
- Visual navigation alone: strong moat, 12 to 24+ months to revenue, hardware cost, heavy
  competition from funded navigation companies.
- Integrity first: sellable now with software only, uses data the customer already has,
  creates the labeled replay corpus that Phase 2 needs, and grows into Option A naturally.

## Positioning
"The fleet picture that tells you which positions to trust, and keeps working when the
network and GNSS do not."

## Principles
Edge first, offline first, deterministic, open standards, small attack surface, honest
about what a heuristic score can and cannot claim.
