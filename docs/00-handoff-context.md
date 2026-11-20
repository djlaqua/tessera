# Handoff Context

Last updated: 2026-11-19

## One paragraph state
Founder evaluated two geospatial startup options (A: GPS-denied terrain/landmark
matcher, B: multi-sensor interoperability middleware). Chosen direction is the
hybrid "dual-use" path: build B first as the commercial wedge, add A as the
deep-tech differentiator. A starter code scaffold exists. Next action is Sprint 01.

## Decisions made
| ID | Decision | Status |
| :--- | :--- | :--- |
| D1 | Hybrid path: B first (months 1 to 3), A module after (months 4 to 6+) | Accepted |
| D2 | Civil and critical-infrastructure first, no classified work in Phase 1 | Accepted |
| D3 | Python 3.12 core, Rust only where profiling demands | Proposed (ADR-001) |
| D4 | SQLite WAL append-only event log, deterministic replay as the core primitive | Proposed (ADR-002) |
| D5 | Sell in English to private and international customers first | Accepted |

## Founder facts (from the founder's own evaluation doc, unverified)
- Based in Germany (Bavaria/Munich ecosystem), strong English, limited German.
- Non-EU passport today; planning German naturalization around early 2028. All legal timelines are `VERIFY`.
- Solo founder, very low early budget for B, moderate to high for A hardware.

## Source claims that need verification
- BAFA and EU dual-use export rules scope for software.
- NATO DIANA and EU program eligibility (incorporation and ownership rules).
- Residence permit rules for self-employment and registering a UG/GmbH.
- Employer IP and moonlighting clauses.
- Procurement timelines (3 to 9 months civil, 12 to 24+ months for A).

## Open questions
1. Which single first customer segment: civil drone operators, utilities, ports, or EMS?
2. Open-source core (TAK-adjacent) with paid edge/enterprise features, or closed?
3. Solo or find a German-speaking commercial co-founder, and when?
4. Which GNSS-denied sub-problem for A: cross-seasonal matching or integrity scoring? (Recommendation: integrity scoring.)

## Next actions
1. Run Sprint 01 (`specs/sprint-01.md`).
2. Complete `docs/08-research-backlog.md` items R1 to R4 this week.
3. Book 5 customer discovery calls before building the MAVLink adapter beyond the spike.

## Paste-in prompt for a new chat or platform
```
You are continuing a project called Tessera. Read the attached AGENTS.md,
docs/00-handoff-context.md, docs/05-architecture.md and the rules/ files.
Follow the rules strictly. Keep explanations brief. Never use em dashes or the
word "erm". Current task: specs/sprint-01.md. Ask before deviating from any
accepted decision in docs/07-decision-log.md. Mark unverified legal or market
claims as VERIFY.
```
