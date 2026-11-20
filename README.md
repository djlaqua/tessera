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

Requires **Python 3.11 or newer** (3.12 recommended, see `.python-version`).

```bash
# macOS: brew install python@3.12   (or: pyenv install 3.12)
python3.12 -m venv .venv && source .venv/bin/activate
python --version            # must print 3.11 or higher
pip install -e ".[dev]"
pytest
pre-commit install          # ruff, mypy, gitleaks, no-em-dash, hygiene hooks
```

If you already created a venv with an older Python, delete it and recreate it:
`deactivate; rm -rf venv .venv; python3.12 -m venv .venv`.

## Docker

```bash
docker build -t tessera .
docker run --rm tessera --help
docker compose -f docker-compose.sitl.yml up --build --abort-on-container-exit --exit-code-from tessera
```
CI builds and smoke tests the image on every push (`docker` job), and a manual `sitl-e2e`
workflow runs the full SITL compose stack.

## Migrating to another chat or platform

1. Upload this folder (or the zip) or paste `docs/00-handoff-context.md` plus `AGENTS.md`.
2. Use the prompt at the bottom of `docs/00-handoff-context.md`.
3. Keep `docs/07-decision-log.md` current; it is the source of truth for decisions.
