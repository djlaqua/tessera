"""Deterministic link degradation simulator for tests and demos."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class DegradedPacket:
    delay_s: float
    payload: bytes


def degrade(
    packets: Sequence[bytes],
    *,
    loss: float = 0.0,
    duplicate: float = 0.0,
    reorder: float = 0.0,
    base_delay_s: float = 0.0,
    jitter_s: float = 0.0,
    seed: int = 0,
) -> list[DegradedPacket]:
    """Apply loss, duplication, reordering and jitter. Same seed gives the same result.

    Probabilities are in [0, 1]. Reordering swaps a packet with its successor.
    """
    for name, value in (("loss", loss), ("duplicate", duplicate), ("reorder", reorder)):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0, 1]")
    if base_delay_s < 0 or jitter_s < 0:
        raise ValueError("delays must be >= 0")
    rng = random.Random(seed)  # noqa: S311 (simulation, not security)
    out: list[bytes] = []
    for packet in packets:
        if rng.random() < loss:
            continue
        out.append(packet)
        if rng.random() < duplicate:
            out.append(packet)
    for index in range(len(out) - 1):
        if rng.random() < reorder:
            out[index], out[index + 1] = out[index + 1], out[index]
    return [DegradedPacket(base_delay_s + rng.uniform(0.0, jitter_s), payload) for payload in out]
