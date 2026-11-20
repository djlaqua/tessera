"""UDP ingest loop: socket -> adapter -> event log."""

from __future__ import annotations

import socket

from tessera.adapters.base import Adapter
from tessera.errors import AdapterError
from tessera.eventlog import EventLog

_RECV_BYTES = 65_535


def ingest_socket(
    sock: socket.socket,
    log: EventLog,
    adapter: Adapter,
    *,
    max_events: int | None = None,
    idle_timeout_s: float | None = None,
) -> int:
    """Read datagrams until `max_events` are stored or the socket is idle.

    Returns the number of observations appended. Oversized datagrams are dropped.
    """
    sock.settimeout(idle_timeout_s)
    stored = 0
    while max_events is None or stored < max_events:
        try:
            raw = sock.recv(_RECV_BYTES)
        except TimeoutError:
            break
        try:
            observations = adapter.parse(raw)
        except AdapterError:
            continue
        for observation in observations:
            log.append(observation)
            stored += 1
            if max_events is not None and stored >= max_events:
                break
    return stored


def bind_udp(host: str, port: int) -> socket.socket:
    """Create a UDP socket bound to `host:port` (loopback by default in the CLI)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    return sock
