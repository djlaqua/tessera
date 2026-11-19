# AGENTS.md

## Project
Tessera: edge-first spatial stream engine. Ingests heterogeneous telemetry
(MAVLink, AIS, MQTT, GeoJSON), normalizes to a canonical model, stores an
append-only event log, replays deterministically, and emits standard formats
(Cursor-on-Target, GeoJSON) over unreliable links. Later: pluggable localization
module producing position fixes with an integrity score.

## Read first
1. `docs/00-handoff-context.md` (state and decisions)
2. `docs/05-architecture.md` (design)
3. `rules/coding-standards.md`, `rules/security.md`, `rules/writing-style.md`
4. `specs/sprint-01.md` (current work)

## Hard rules
- Follow the rules files explicitly. Do not deviate. If a rule blocks the task, stop and ask.
- Brief explanations. No filler. Never use the word "erm". Never use em dashes in prose, comments, or documents.
- Clean, typed, tested, professional code. No dead code, no TODO without an issue reference.
- Security first: validate all external input, no secrets in code, pinned dependencies, safe XML and deserialization.
- Record every architectural decision in `docs/07-decision-log.md` using the `write-adr` skill.
- Do not add a dependency without stating why and the alternative considered.
- Claims about law, export control, procurement, or competitors must be marked `VERIFY` until sourced.

## Stack (see ADR-001)
Python 3.12, pydantic v2, asyncio, SQLite (WAL), pyproj, FastAPI + MapLibre (later), pytest, ruff, mypy strict.

## Commands
```bash
pytest -q
ruff check . && ruff format --check .
mypy src
```

## Definition of done
Tests pass, lint and mypy clean, public functions typed and documented, decision log updated if design changed.

## Agents and skills
Role prompts live in `agents/`. Procedures live in `skills/<name>/SKILL.md`.
