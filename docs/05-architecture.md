# Architecture

## Overview
```
 sources              edge (tessera ingest / sync / map)                   hub (tessera hub)
 MAVLink --\                                                       signed     +-------------+
 AIS     ---+--> adapters --> event log (SQLite WAL) --> uplink ---batches--> | hub store   |
 JSON    --/    validation        |        |            (zlib,     HTTPS     | (idempotent)|
                                replay   live map        Ed25519)            | live map    |
                                  |      + integrity                         | + integrity |
                              CoT/GeoJSON                                    +-------------+
                                         LocalizationProvider plugins (Phase 2, private repo)
```

## Components
| Component | Responsibility |
| :--- | :--- |
| Adapter | Parse one protocol, validate, emit `Observation`. Pure, no I/O side effects beyond its transport |
| Normalizer | Convert CRS to WGS84, units to SI, timestamps to UTC with source clock offset |
| Event log | Append-only, ordered by `(ingest_seq)`, immutable, schema versioned |
| Replay engine | Reads the log, emits events at speed factor, deterministic given the same log |
| Encoders | `Observation` to CoT XML, GeoJSON |
| Uplink (edge) | Reads after the acknowledged cursor, sends batches of up to 500 events, backs off exponentially on failure, rewinds when the hub reports a gap |
| Hub | Verifies Ed25519 batch signatures per edge, stores rows idempotently keyed by (edge_id, edge_seq), returns its cursor |
| Live view | Reads the newest events read-only, builds per-entity tracks, scores integrity, compares sources of the same platform |
| Integrity v0 | Kinematic and motion-consistency checks per track, cross-source agreement per platform (`tessera.integrity`) |
| Server | FastAPI app: `/v1/sync` (hub only), `/v1/features`, `/v1/config`, `/healthz`, static map with vendored Leaflet |
| LocalizationProvider | Phase 2 plugin: sensor frames in, `PositionFix` with covariance and integrity out |

## Canonical data model
`Observation`
- `id` (uuid4), `source_id`, `entity_id`, `entity_type` (uav, vessel, sensor, ground)
- `observed_at` (UTC, from source), `ingested_at` (UTC, local)
- `position` (lat, lon, alt_m, optional)
- `velocity` (course_deg, speed_mps, optional)
- `position_accuracy_m` (optional), `attributes` (bounded dict of scalars)
- `schema_version`

`PositionFix` (Phase 2): `Observation` fields plus `covariance`, `integrity` (0 to 1), `method`, `evidence_refs`.

## Interfaces
```python
class Adapter(Protocol):
    name: str

    def parse(self, raw: bytes) -> Iterable[Observation]: ...


class LocalizationProvider(Protocol):
    def update(self, frame: SensorFrame) -> PositionFix | None: ...
```

## Sync protocol (ADR-009)
1. Edge reads events after `sync_state.acked_seq` for that hub.
2. Batch = JSON envelope with `edge_id`, `first_seq`, `last_seq`, `count`, payload SHA-256,
   zlib payload of `<seq> TAB <observation json>` lines, Ed25519 signature over a domain tag
   and all header fields.
3. Hub checks the edge is trusted, verifies the signature, the hash, decompression bounds
   (8 MiB) and sequence order, then inserts with `INSERT OR IGNORE` and returns its cursor.
4. A batch that starts after a gap is not stored; the returned cursor makes the edge resend.
5. Duplicate batches are harmless; at-least-once delivery, exactly-once storage.

## Non functional requirements
- Target: runs on a Raspberry Pi 5 class device, under 150 MB RAM idle (not yet measured).
- No data loss on link or power loss (WAL, fsync policy configurable).
- Deterministic replay: same log gives byte-identical output.
- All external input bounded and validated.

## Security design
Edges authenticate by Ed25519 signatures on every batch (keys created with mode 0600 and
refused if readable by others). The hub authenticates to edges with TLS 1.3 server
certificates. Read endpoints accept an optional bearer token. Bodies capped at 2 MiB, no
OpenAPI endpoints, strict CSP and security headers, generic auth errors. Containers run
non-root, read-only, with all capabilities dropped. MAVLink links can require signing.
Gaps tracked in `specs/sprint-04.md`: dependency lock with hashes, structured logs, SBOM.
See `rules/security.md`.

## Technology choices
See ADRs in `07-decision-log.md`. Python 3.12, pydantic v2, SQLite WAL, pyproj, pymavlink,
cryptography (Ed25519), FastAPI and uvicorn, Leaflet 1.9.4 vendored (ADR-010).
