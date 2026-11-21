# Tessera (working name)

A fleet picture that tells you which positions to trust, and keeps working when the network
and GNSS do not. Edge telemetry engine (MAVLink, AIS, JSON) with signed store-and-forward
sync, a live map, and position integrity scoring.

Status: engineering through pilot readiness is built and tested; see `docs/00-handoff-context.md`.
No license yet: all rights reserved (ADR-012).

## Try it in one command
```bash
docker compose -f docker-compose.demo.yml up --build -d
open http://127.0.0.1:8080      # a simulated copter flies; at about 45 s its GPS is glitched
```
The raw GPS track turns red while the autopilot's fused track stays green. Details: `docs/deployment.md`.

## CLI
| Command | Purpose |
| :--- | :--- |
| `tessera ingest --protocol mavlink\|ais\|json --db edge.db` | Store telemetry from UDP (loopback by default) |
| `tessera replay --db edge.db --format geojson\|cot` | Stream the log out |
| `tessera integrity --db edge.db` | List fixes with low integrity |
| `tessera keygen --out edge-1.key` | Create sync keys |
| `tessera sync --db edge.db --hub-url https://hub --edge-id edge-1 --key edge-1.key` | Send the log to a hub |
| `tessera hub --db hub.db --trusted-keys keys/` | Hub with live map |
| `tessera map --db edge.db` | Live map on the edge |

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
| `docs/09-discovery-kit.md` | Customer discovery call script and qualification |
| `docs/deployment.md` | Demo, edge and hub deployment |
| `docs/sitl-quickstart.md` | ArduPilot SITL without Docker |
| `rules/` | Coding, security, writing rules |
| `agents/` | Role prompts (architect, backend, geo, reviewer, researcher, strategist) |
| `skills/` | Repeatable procedures (adapter, ADR, replay test) |
| `specs/` | Sprint specs (01 to 03 done, 04 next) |
| `deploy/systemd/` | Hardened service units |
| `src/`, `tests/` | Code and tests |

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
CI builds the image, runs a hardened ingest, replay and signed sync smoke test on every push
(`docker` job). The `sitl-e2e` workflow runs SITL ingest and the full demo, and checks that
the hub flags the injected GPS glitch.

## Migrating to another chat or platform

1. Upload this folder (or the zip) or paste `docs/00-handoff-context.md` plus `AGENTS.md`.
2. Use the prompt at the bottom of `docs/00-handoff-context.md`.
3. Keep `docs/07-decision-log.md` current; it is the source of truth for decisions.
