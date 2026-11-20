# Sprint 02: Ingest breadth and resilience (about 2 weeks)

## Goal
Run against live SITL, add a second protocol, and make the pipeline resilient on bad links.

## Scope
| # | Task | Acceptance |
| :--- | :--- | :--- |
| 1 | Live SITL verification and a recorded sample log (synthetic only) in `tests/fixtures/` | Replay of the fixture is deterministic |
| 2 | Docker compose: SITL plus tessera (ADR-006) | `docker compose up` produces a log |
| 3 | MQTT adapter (`skills/add-protocol-adapter`) | Bounded, fuzzed, tested |
| 4 | AIS adapter (NMEA 0183 `!AIVDM` position reports) | Checksums verified, bad sentences dropped |
| 5 | MAVLink signing verification (ADR-005) | Unsigned or badly signed frames rejected when enabled |
| 6 | Link degradation simulator (loss, delay, reorder) for tests | Ingest keeps order by `ingest_seq` |
| 7 | CRS normalizer using pyproj | Known EPSG fixtures round trip within 1 cm |

## Out of scope
UI, sync, localization.
