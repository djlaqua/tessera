---
name: replay-test
description: Verify deterministic replay of the event log. Use after changing the log, normalizer, or encoders.
---

# Replay determinism test

1. Build a fixture log of at least 1,000 mixed observations with a fixed seed.
2. Replay twice at speed factor 0 (as fast as possible) through an encoder, collect output bytes.
3. Assert both runs are byte identical.
4. Replay with a fake clock at speed 1.0 and assert inter-event delays match `observed_at` deltas.
5. Corrupt one row and assert replay fails loudly with `LogCorruptionError`.
6. Add the case to `tests/test_replay.py`.
