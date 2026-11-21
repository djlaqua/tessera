# Handoff Context

Last updated: 2026-11-21

## One paragraph state
Tessera is a hybrid dual-use product: an edge telemetry engine (Option B) that carries a
position integrity layer (first step of Option A). Built and verified so far: canonical
model, append-only log, deterministic replay, CoT and GeoJSON output, MAVLink (with signing,
fused and raw GPS), AIS and JSON adapters, CRS normalizer, link simulator, signed
store-and-forward sync to a hub, a live map with per-track and cross-source integrity
scores, Docker images, a full demo stack (simulated copter, GPS glitch, edge, hub) and
systemd units. The engineering roadmap through pilot readiness is done; the business gates
(discovery calls, first pilot) are not. Next action: discovery calls with the demo.

## Decisions made
| ID | Decision | Status |
| :--- | :--- | :--- |
| D1 | Hybrid path: B first, A as integrity layer | Accepted (ADR-000, ADR-003) |
| D2 | Civil and critical-infrastructure first, no classified work in Phase 1 | Accepted |
| D3 | Python 3.12 core, Rust only where profiling demands | Accepted (ADR-001) |
| D4 | SQLite WAL append-only event log, deterministic replay | Accepted (ADR-002) |
| D5 | Sell in English to private and international customers first | Accepted |
| D6 | Signed batch sync over HTTPS, idempotent hub | Accepted (ADR-009) |
| D7 | Lead positioning with GNSS integrity, carried by the telemetry engine | Proposed (ADR-011) |
| D8 | Public core repo, Phase 2 localization in a private repo until export review | Proposed (ADR-012) |

## Founder facts (from the founder's own evaluation doc, unverified)
- Based in Germany (Bavaria/Munich ecosystem), strong English, limited German.
- Personal legal and residency timelines are tracked privately (`private/`, gitignored). All legal timelines are `VERIFY`.
- Solo founder, very low early budget for B, moderate to high for A hardware.

## Source claims that need verification
- BAFA and EU dual-use export rules scope for software, including whether public code is affected (ADR-012).
- NATO DIANA and EU program eligibility (incorporation and ownership rules).
- Residency rules for self-employment and registering a UG/GmbH.
- Employer IP and moonlighting clauses.
- Procurement timelines (3 to 9 months civil, 12 to 24+ months for A).

## Open questions
1. Which single first customer segment: civil drone operators, utilities, ports, or EMS? (`docs/09-discovery-kit.md`)
2. License: proprietary, source-available, or open core? (ADR-012)
3. Solo or find a German-speaking commercial co-founder, and when?
4. Should the hub be offered as a hosted service or customer-hosted only?

## Next actions
1. Run 5 discovery calls using `docs/09-discovery-kit.md` and the demo stack.
2. Book an export-control and IP review before any Phase 2 localization code (ADR-012).
3. Sprint 04 (`specs/sprint-04.md`): dependency lock, structured logs, replay scrubber, PX4 check.

## Paste-in prompt for a new chat or platform
```
You are continuing a project called Tessera. Read the attached AGENTS.md,
docs/00-handoff-context.md, docs/05-architecture.md and the rules/ files.
Follow the rules strictly. Keep explanations brief. Never use em dashes or the
word "erm". Current task: specs/sprint-04.md. Ask before deviating from any
accepted decision in docs/07-decision-log.md. Mark unverified legal or market
claims as VERIFY.
```
