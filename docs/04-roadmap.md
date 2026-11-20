# Roadmap

## Phase gates
| Gate | Condition to advance |
| :--- | :--- |
| G1 | 3 of 5 discovery calls confirm the pain and a first segment is chosen |
| G2 | Replay demo working on real recorded data from a design partner |
| G3 | One paid pilot or grant secured |
| G4 | Replay harness can score a localization candidate against ground truth |

## Weeks 1 to 2: Foundation
Sprint 01 (`specs/sprint-01.md`): canonical model, event log, replay, CoT encoder, tests, CI.
Research R1 to R4. Five discovery calls booked.

## Weeks 3 to 6: Ingest
MAVLink adapter (ArduPilot/PX4 SITL), AIS adapter, MQTT adapter, GeoJSON export, CRS handling.

## Weeks 7 to 10: Resilience and UI
Store-and-forward sync with delta compression, link degradation simulator, FastAPI + MapLibre live map and replay scrubber.

## Weeks 11 to 13: Pilot readiness
Hardening, packaging (container plus systemd unit), docs, demo video, pilot proposal.

## Months 4 to 6: Option A module
Define `LocalizationProvider` plugin API. Prototype integrity scoring on recorded flights with open DEM and orthoimagery. Evaluate cross-seasonal matching only if integrity scoring shows traction.

## Not in scope until G3
Classified work, military hardware integration, custom hardware, mobile apps.
