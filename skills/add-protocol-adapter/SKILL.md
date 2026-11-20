---
name: add-protocol-adapter
description: Add a new input protocol adapter (MAVLink, AIS, MQTT, GeoJSON, etc.) that parses raw bytes into validated Observations. Use when adding or changing a data source.
---

# Add a protocol adapter

1. Read `docs/05-architecture.md` and `rules/security.md`.
2. Create `src/tessera/adapters/<name>.py` implementing the `Adapter` protocol (`name`, `parse(raw) -> Iterable[Observation]`).
3. Enforce limits first: max message size, field ranges (lat -90..90, lon -180..180), required fields.
4. Map to `Observation`; convert units to SI; keep source timestamp in `observed_at`.
5. Raise `AdapterError` subclasses on invalid input; never return partial garbage.
6. Add fixtures under `tests/fixtures/<name>/` (real captures, anonymized).
7. Tests: valid message, truncated, oversized, out of range, hostile bytes, hypothesis fuzz.
8. Register in the adapter registry; document in README table.
9. Run `pytest`, `ruff`, `mypy --strict`.
