"""Edge side: send unacknowledged events to a hub, with retry and exponential backoff."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tessera.eventlog import EventLog
from tessera.sync.batch import MAX_BATCH_EVENTS, Ack, SyncBatch, build_batch
from tessera.sync.errors import SyncError, TransportError


class Transport(Protocol):
    def send(self, batch: SyncBatch) -> Ack:
        """Deliver a batch and return the hub acknowledgement.

        Raises:
            TransportError: on link failure (the caller retries later).
        """
        ...


class Uplink:
    """Reads the event log after the acknowledged cursor and sends it in batches."""

    def __init__(
        self,
        log: EventLog,
        *,
        peer: str,
        edge_id: str,
        key: Ed25519PrivateKey,
        transport: Transport,
        max_events: int = MAX_BATCH_EVENTS,
    ) -> None:
        if not 1 <= max_events <= MAX_BATCH_EVENTS:
            raise ValueError(f"max_events must be in [1, {MAX_BATCH_EVENTS}]")
        self._log = log
        self._peer = peer
        self._edge_id = edge_id
        self._key = key
        self._transport = transport
        self._max_events = max_events

    def run_once(self) -> int:
        """Send one batch. Returns events newly acknowledged (0 if nothing was sent)."""
        cursor = self._log.get_cursor(self._peer)
        rows = list(self._log.read(after_seq=cursor, limit=self._max_events))
        if not rows:
            return 0
        ack = self._transport.send(build_batch(self._edge_id, rows, self._key))
        if ack.edge_id != self._edge_id:
            raise SyncError("acknowledgement is for a different edge")
        if ack.acked_seq > rows[-1][0]:
            raise SyncError("acknowledgement is ahead of what was sent")
        self._log.set_cursor(self._peer, ack.acked_seq)
        return max(0, ack.acked_seq - cursor)

    def drain(self) -> int:
        """Send batches until no progress is made. Returns the total newly acknowledged.

        The cursor can move backward when the hub reports a gap (for example after a hub
        restore); the next iteration then resends from that point.
        """
        total = 0
        while True:
            before = self._log.get_cursor(self._peer)
            total += self.run_once()
            if self._log.get_cursor(self._peer) == before:
                return total

    def run(
        self,
        *,
        interval_s: float = 5.0,
        max_backoff_s: float = 60.0,
        sleep: Callable[[float], None] = time.sleep,
        should_stop: Callable[[], bool] = lambda: False,
    ) -> None:
        """Drain, then wait, until `should_stop`. Backs off exponentially on link failure."""
        delay = interval_s
        while not should_stop():
            try:
                self.drain()
                delay = interval_s
            except TransportError:
                delay = min(delay * 2, max_backoff_s)
            sleep(delay)
