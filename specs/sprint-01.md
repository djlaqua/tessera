# Sprint 01: Foundation (about 1 to 2 weeks)

## Goal
A tested core: canonical model, durable event log, deterministic replay, CoT and GeoJSON encoders.

## Scope
| # | Task | Acceptance |
| :--- | :--- | :--- |
| 1 | Repo, `pyproject.toml`, ruff, mypy strict, pytest, CI | `pytest`, `ruff`, `mypy` run clean |
| 2 | `Observation` model with validation | Out of range inputs rejected |
| 3 | `EventLog` (SQLite WAL, append, read, count) | Survives reopen, ordered by `ingest_seq` |
| 4 | `Replayer` with speed factor and injectable sleep | Deterministic, ordered |
| 5 | CoT encoder | Valid XML, escapes attributes, stable output |
| 6 | GeoJSON encoder | Valid FeatureCollection, lon/lat order |
| 7 | MAVLink spike (separate branch) | Read `GLOBAL_POSITION_INT` from ArduPilot SITL into the log |

Tasks 1 to 6 are scaffolded in `src/` and `tests/`. Verify, extend, then do 7.

## Out of scope
UI, sync, AIS, MQTT, localization.

## Next sprint
Adapters (MAVLink full, AIS, MQTT), CRS normalization, link degradation simulator.
