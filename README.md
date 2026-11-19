# Tessera (working name)

Resilient spatial stream engine for degraded-network, GNSS-contested environments.
Phase 1 ships a **Spatial Stream & Replay Engine** (Option B). Phase 2 plugs in an
**integrity-scored visual/DEM localization module** (Option A).

## Pack index

| Path | Purpose |
| :--- | :--- |
| `AGENTS.md` | Universal agent instructions (Claude Code, Codex, Cursor, others) |
| `CLAUDE.md` | Thin pointer to `AGENTS.md` |
| `docs/00-handoff-context.md` | State, decisions, open questions, paste-in prompt for a new chat |
| `docs/01-vision-and-strategy.md` | Thesis, wedge, positioning |
| `docs/02-market-and-competition.md` | Option comparison, competition, verification TODOs |
| `docs/03-business-plan.md` | Customers, pricing, GTM, costs, milestones |
| `docs/04-roadmap.md` | 90 day plan and phase gates |
| `docs/05-architecture.md` | System design, data model, interfaces |
| `docs/06-founder-constraints-and-compliance.md` | Legal, export, employer, language constraints (verify) |
| `docs/07-decision-log.md` | ADRs, append only |
| `docs/08-research-backlog.md` | Open questions to research |
| `rules/` | Coding, security, writing rules |
| `agents/` | Role prompts (architect, backend, geo, reviewer, researcher, strategist) |
| `skills/` | Repeatable procedures (adapter, ADR, replay test) |
| `specs/sprint-01.md` | First coding sprint |
| `src/`, `tests/` | Verified starter scaffold |

## Quick start

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Migrating to another chat or platform

1. Upload this folder (or the zip) or paste `docs/00-handoff-context.md` plus `AGENTS.md`.
2. Use the prompt at the bottom of `docs/00-handoff-context.md`.
3. Keep `docs/07-decision-log.md` current; it is the source of truth for decisions.
