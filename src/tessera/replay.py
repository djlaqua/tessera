"""Deterministic replay of an event log."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator

from tessera.eventlog import EventLog
from tessera.models import Observation


class Replayer:
    """Replays observations in ingest order.

    `speed` is a multiplier on recorded time. 0 replays as fast as possible.
    `sleep` is injectable so tests run without real delays.
    """

    def __init__(
        self,
        log: EventLog,
        *,
        speed: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if speed < 0:
            raise ValueError("speed must be >= 0")
        self._log = log
        self._speed = speed
        self._sleep = sleep

    def __iter__(self) -> Iterator[Observation]:
        previous: Observation | None = None
        for _, observation in self._log.read():
            if previous is not None and self._speed > 0:
                delta = (observation.observed_at - previous.observed_at).total_seconds()
                if delta > 0:
                    self._sleep(delta / self._speed)
            previous = observation
            yield observation
