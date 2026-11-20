# Architecture

## Overview
```
 sources                 edge daemon (tessera)                          consumers
 MAVLink  --\                                                         /-- CoT (TAK)
 AIS      ---+--> adapters --> normalizer --> event log (SQLite WAL) --+--- GeoJSON / REST
 MQTT     ---+       |             |                  |               \-- WebSocket map UI
 GeoJSON  --/   validation     CRS (pyproj)     replay engine
                                                      |
                                           sync (store-and-forward, delta)  --> cloud hub
                                                      |
                                    LocalizationProvider plugins (Phase 2)
```

## Components
| Component | Responsibility |
| :--- | :--- |
| Adapter | Parse one protocol, validate, emit `Observation`. Pure, no I/O side effects beyond its transport |
| Normalizer | Convert CRS to WGS84, units to SI, timestamps to UTC with source clock offset |
| Event log | Append-only, ordered by `(ingest_seq)`, immutable, schema versioned |
| Replay engine | Reads the log, emits events at speed factor, deterministic given the same log |
| Encoders | `Observation` to CoT XML, GeoJSON |
| Sync | Ship log segments upstream with ack, resume, delta compression, priority queue |
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

## Non functional requirements
- Runs on a Raspberry Pi 5 class device, under 150 MB RAM idle.
- No data loss on link or power loss (WAL, fsync policy configurable).
- Deterministic replay: same log gives byte-identical output.
- All external input bounded and validated.

## Security design
Least privilege service user, TLS 1.3 with mutual auth for sync, signed log segments (Ed25519), defusedxml for any XML parsing, no pickle, secrets from environment or secret store, SBOM and pinned hashes. See `rules/security.md`.

## Technology choices
See ADRs in `07-decision-log.md`. Python 3.12, pydantic v2, asyncio, SQLite WAL, pyproj, FastAPI, MapLibre GL JS.
