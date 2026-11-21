# Sprint 04: Hardening and pilot polish (about 2 weeks)

## Goal
Close the known security and operability gaps before the first pilot.

| # | Task | Acceptance |
| :--- | :--- | :--- |
| 1 | Dependency lock with hashes (`uv pip compile --generate-hashes` or pip-tools) used by Docker and CI | Image builds from the lock; CI fails on drift |
| 2 | Structured JSON logs with a redaction helper (no coordinates at INFO) | Log schema documented, test for redaction |
| 3 | SBOM (CycloneDX) in CI and image digest pinning | SBOM artifact on every main build |
| 4 | Replay scrubber in the map (time slider over a stored window) | Works on the demo log |
| 5 | Offline basemap option (local MBTiles or a static tile directory) | Map renders with no internet |
| 6 | PX4 SITL check of the MAVLink adapter | Same tests pass on PX4 output |
| 7 | Retention: prune events older than N days on edge after hub ack | Never deletes unacknowledged events |
| 8 | Measure RAM and CPU on a Raspberry Pi class device | Numbers recorded in docs/05 |

## Out of scope
Phase 2 localization code (private repo, ADR-012), multi-tenant hub, SSO.
