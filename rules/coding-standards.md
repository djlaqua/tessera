# Coding Standards

- Python 3.12, full type hints, `mypy --strict` clean, `ruff` clean.
- Small pure functions. Side effects only at edges (transport, storage).
- Dataclasses or pydantic models for data. No untyped dicts crossing module boundaries.
- Immutable models (`frozen=True`) for events.
- Explicit errors: custom exception hierarchy, never bare `except`, never swallow.
- No global mutable state. Inject dependencies.
- Time: always timezone-aware UTC. Never `datetime.now()` without tz. Inject a clock for tests.
- Units: SI internally (meters, seconds, m/s, degrees for angles at the boundary).
- Docstrings on public API: one line summary, args, raises.
- Tests: pytest, one behavior per test, deterministic, no network. Property tests (hypothesis) for parsers.
- Names describe intent. No abbreviations beyond domain terms (CRS, CoT, AIS).
- Commits: conventional commits. One logical change each.
- Dependencies: minimal, pinned, justified in the PR or ADR.
