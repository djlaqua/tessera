# AGENTS.md

## Project
Tessera: edge-first telemetry engine with position integrity. Ingests MAVLink, AIS and
JSON telemetry, normalizes to a canonical model, stores an append-only event log, replays
deterministically, emits CoT and GeoJSON, syncs signed batches to a hub, and scores how
far each position can be trusted. Phase 2 adds independent position sources (private repo).

## Read first
1. `docs/00-handoff-context.md` (state and decisions)
2. `docs/05-architecture.md` (design)
3. `rules/coding-standards.md`, `rules/security.md`, `rules/writing-style.md`
4. `specs/sprint-04.md` (current work)

## Hard rules
- Follow the rules files explicitly. Do not deviate. If a rule blocks the task, stop and ask.
- Brief explanations. No filler. Never use the word "erm". Never use em dashes in prose, comments, or documents.
- Clean, typed, tested, professional code. No dead code, no TODO without an issue reference.
- Security first: validate all external input, no secrets in code, pinned dependencies, safe XML and deserialization.
- Record every architectural decision in `docs/07-decision-log.md` using the `write-adr` skill.
- Do not add a dependency without stating why and the alternative considered.
- Claims about law, export control, procurement, or competitors must be marked `VERIFY` until sourced.

## Stack (see ADR-001)
Python 3.12, pydantic v2, SQLite (WAL), pyproj, pymavlink, cryptography, FastAPI + uvicorn, Leaflet (vendored), pytest, hypothesis, ruff, mypy strict.

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
