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
