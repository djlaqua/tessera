# Decision Log (append only)

Format: ID, date, status, context, decision, consequences.

## ADR-000: Hybrid path
- Date: 2026-11-19, Status: Accepted
- Context: Option A has the deeper moat but slow revenue and hardware cost; Option B ships fast with a weaker moat.
- Decision: Build B first as Spatial Stream & Replay Engine, add A as an integrity-scoring module on the same engine.
- Consequences: Revenue path in months 3 to 9, replay harness doubles as A's validation tool.

## ADR-001: Python first
- Date: 2026-11-19, Status: Proposed
- Context: Solo founder, need speed, later CV work is Python.
- Decision: Python 3.12 with strict typing. Port hot paths to Rust only after profiling.
- Consequences: Faster iteration, higher memory use on edge devices, clear interfaces keep a later port possible.

## ADR-002: SQLite WAL event log
- Date: 2026-11-19, Status: Proposed
- Context: Need durable, append-only, queryable storage on small devices with power loss risk.
- Decision: SQLite in WAL mode, one `events` table, monotonic `ingest_seq`, JSON payload with schema version.
- Consequences: Simple and robust. Revisit Parquet segments for long retention and analytics.

## ADR-003: Integrity scoring before full navigation
- Date: 2026-11-19, Status: Proposed
- Context: Full visual navigation faces heavy competition.
- Decision: Phase 2 targets a trust score on any position source before attempting a complete navigation stack.
- Consequences: Smaller scope, works with existing autopilots.

## ADR-004: Explicit altitude datum
- Date: 2026-11-20, Status: Accepted
- Context: MAVLink reports altitude above mean sea level, while CoT `hae` and GeoJSON z expect ellipsoid height. Treating them as equal introduces errors of tens of meters. Alternative rejected: silently converting with a geoid model (adds a heavy dependency and hides assumptions).
- Decision: `Position.alt_ref` (`ellipsoid` default, or `msl`). Encoders emit `hae` and GeoJSON z only for ellipsoid heights. MSL heights go to the `alt_msl_m` property.
- Consequences: No false precision. A geoid conversion can be added later as a normalizer step.

## ADR-005: pymavlink for MAVLink parsing
- Date: 2026-11-20, Status: Accepted
- Context: A hand-written MAVLink parser adds attack surface and maintenance. Alternative rejected: custom frame parser.
- Decision: Use `pymavlink` (v2 common dialect, robust parsing, 64 KiB chunk limit). MAVLink signing is not verified yet.
- Consequences: Telemetry is treated as untrusted. Add signing verification before any pilot that relies on link authenticity (see sprint 02).

## ADR-006: Containers later, not now
- Date: 2026-11-20, Status: Proposed
- Context: Docker helps with SITL, ARM images and pilot packaging but adds overhead early.
- Decision: Add a SITL compose file in sprint 02, production image in weeks 11 to 13.
- Consequences: Sprints 01 and 02 stay on a plain venv.

## ADR-007: Sprint 02 dependencies
- Date: 2026-11-20, Status: Accepted
- Context: CRS handling and AIS validation need trusted references. Alternatives rejected: hand-written projection math, hand-trusted AIS bit tables without an oracle.
- Decision: `pyproj` is a runtime dependency (CRS normalization, `always_xy=True`). `pyais` is a dev-only dependency used as an independent oracle in AIS tests. The AIS decoder itself is a small in-repo implementation limited to types 1 to 3.
- Consequences: Runtime stays small. AIS decoder correctness is cross-checked against an established library on every test run.

## ADR-008: MAVLink signing enforcement
- Date: 2026-11-20, Status: Accepted (supersedes the signing caveat in ADR-005)
- Context: Unsigned MAVLink can be spoofed by anyone who can reach the port. pymavlink verifies signatures and replay timestamps.
- Decision: `MavlinkAdapter(signing_key=...)` requires valid signatures and rejects unsigned, wrongly signed and replayed frames. The CLI reads the key from `--signing-key-file`, never from the command line.
- Consequences: Pilots on real links should enable signing. The key must be provisioned and stored outside the repo.

## ADR-009: Signed batch sync over HTTPS
- Date: 2026-11-21, Status: Accepted
- Context: Edges must forward their log over unreliable links without loss, duplication or forgery. Alternatives rejected: mutual TLS per edge (certificate management burden for a solo team), MQTT bridge (adds a broker and still needs end-to-end integrity).
- Decision: Edges send zlib batches signed with Ed25519 over HTTPS. The hub stores idempotently by (edge_id, edge_seq) and returns its cursor; edges resume or rewind from it.
- Consequences: At-least-once delivery, exactly-once storage, end-to-end integrity independent of the transport. Key distribution is manual (`tessera keygen`) for now.

## ADR-010: Leaflet vendored, HTTP polling
- Date: 2026-11-21, Status: Accepted
- Context: The map must work offline and pass a strict CSP. Alternatives rejected: CDN scripts (fail offline, supply chain risk), MapLibre GL (heavier, WebGL), WebSockets (more server state for little gain at 2 s refresh).
- Decision: Vendor Leaflet 1.9.4 with its license and checksum, poll `/v1/features` every 2 s.
- Consequences: Small, auditable UI. Basemap tiles still need a tile server; offline tiles are a Sprint 04 item.

## ADR-011: Integrity v0 scope and claims
- Date: 2026-11-21, Status: Proposed
- Context: Integrity is the commercial differentiator, but certified navigation integrity (RAIM-style) is out of reach and overclaiming is a legal and trust risk.
- Decision: Score each fix with kinematic and motion-consistency checks against the last trusted fix, and compare sources of the same platform (fused estimate vs raw GPS). Present results as a heuristic, never as certified. Lead positioning with integrity, carried by the telemetry engine.
- Consequences: Detects jumps and source disagreement; does not detect a slow, consistent spoof seen by all sources. Phase 2 independent sources address that.

## ADR-012: Repository visibility and licensing
- Date: 2026-11-21, Status: Proposed (needs founder decision and advisor review)
- Context: The repository was made public to unlock free branch protection. It has no license, so it is "all rights reserved" by default. Public code reaches every country, and EU dual-use rules may apply to some navigation software (VERIFY).
- Decision: Keep the core public and unlicensed until the open-core decision. Build any Phase 2 localization code in a separate private repository until an export-control review clears it. Keep business-sensitive notes in `private/`.
- Consequences: Competitors can read the strategy docs. Revisit: choose a license (for example Apache-2.0 core plus proprietary hub) or return to private with a paid plan.
