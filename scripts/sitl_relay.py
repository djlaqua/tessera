"""Relay MAVLink 2 from an ArduPilot SITL TCP port to a UDP address.

SITL exposes MAVLink on TCP 5760 and sends little until a ground station asks for data.
This script announces itself, requests GLOBAL_POSITION_INT at a fixed rate, then forwards
raw bytes to UDP so `tessera ingest-mavlink` can consume them.

Usage:
    python scripts/sitl_relay.py --tcp 127.0.0.1:5760 --udp 127.0.0.1:14550 --seconds 90
"""

from __future__ import annotations

import argparse
import socket
import sys
import time

from pymavlink.dialects.v20 import common as mavlink2

_GLOBAL_POSITION_INT = 33


def _split(address: str) -> tuple[str, int]:
    host, _, port = address.rpartition(":")
    return host, int(port)


def _connect(address: tuple[str, int], deadline: float) -> socket.socket:
    """Connect with retries so the relay can start before the simulator is ready."""
    while True:
        try:
            return socket.create_connection(address, timeout=5)
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(1.0)


def try_send(sock: socket.socket, data: bytes, target: tuple[str, int]) -> bool:
    """Send one datagram. Returns False if the target is unreachable (for example its
    container has exited and its DNS name no longer resolves)."""
    try:
        sock.sendto(data, target)
    except OSError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tcp", default="127.0.0.1:5760")
    parser.add_argument("--udp", default="127.0.0.1:14550")
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--rate-hz", type=float, default=10.0)
    args = parser.parse_args()

    mav = mavlink2.MAVLink(None, srcSystem=255, srcComponent=190)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_target = _split(args.udp)
    deadline = time.monotonic() + args.seconds
    delivered = 0
    dropped = 0
    with _connect(_split(args.tcp), deadline) as tcp:
        tcp.settimeout(1.0)
        heartbeat = mav.heartbeat_encode(
            mavlink2.MAV_TYPE_GCS, mavlink2.MAV_AUTOPILOT_INVALID, 0, 0, 0
        ).pack(mav)
        interval_us = int(1_000_000 / args.rate_hz)
        command = mav.command_long_encode(
            1,
            1,
            mavlink2.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            _GLOBAL_POSITION_INT,
            interval_us,
            0,
            0,
            0,
            0,
            0,
        ).pack(mav)
        tcp.sendall(heartbeat)
        tcp.sendall(command)
        last_heartbeat = time.monotonic()
        while time.monotonic() < deadline:
            if time.monotonic() - last_heartbeat > 1.0:
                tcp.sendall(heartbeat)
                tcp.sendall(command)
                last_heartbeat = time.monotonic()
            try:
                data = tcp.recv(4096)
            except TimeoutError:
                continue
            if not data:
                break
            if try_send(udp, data, udp_target):
                delivered += 1
            else:
                dropped += 1
    print(f"relayed {delivered} datagrams, dropped {dropped}", file=sys.stderr)
    return 0 if delivered else 1


if __name__ == "__main__":
    raise SystemExit(main())
