"""Relay MAVLink 2 from an ArduPilot SITL TCP port to a UDP address, optionally flying a demo.

SITL exposes MAVLink on TCP 5760 and sends little until a ground station asks for data.
This script announces itself, requests GLOBAL_POSITION_INT and GPS_RAW_INT, and forwards
raw bytes to UDP so `tessera ingest --protocol mavlink` can consume them.

With `--fly` it also switches the copter to GUIDED, arms, takes off and flies a square.
With `--glitch-at S --glitch-deg D` it offsets the simulated GPS latitude by D degrees from
S seconds after the circuit starts, for `--glitch-for` seconds (SIM_GPS_GLITCH_X). This
simulates a GNSS spoof for testing integrity scoring. Simulation only.

Usage:
    python scripts/sitl_relay.py --tcp 127.0.0.1:5760 --udp 127.0.0.1:14550 --seconds 90
    python scripts/sitl_relay.py --fly --glitch-at 40 --glitch-deg 0.003 --seconds 150
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from typing import Any

from pymavlink.dialects.v20 import common as mavlink2

_GLOBAL_POSITION_INT = 33
_GPS_RAW_INT = 24
_GUIDED = 4
_ARMED_FLAG = 128
_POSITION_ONLY_MASK = 0x0DF8
_CRUISE_ALT_M = 30.0
_LEG_SECONDS = 25.0
_SQUARE_DEG = ((0.0, 0.0), (0.0027, 0.0), (0.0027, 0.004), (0.0, 0.004))


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


def _log(message: str) -> None:
    print(f"[relay] {message}", file=sys.stderr, flush=True)


class Pilot:
    """Minimal GUIDED-mode flight plan driven by telemetry. Commands are resent until acted on."""

    def __init__(self, mav: Any, glitch_at: float | None, glitch_deg: float, glitch_for: float):
        self._mav = mav
        self.state = "wait_position"
        self._home: tuple[float, float] | None = None
        self._armed = False
        self._mode = -1
        self._rel_alt = 0.0
        self._last_command = 0.0
        self._cruise_start = 0.0
        self._glitch_at = glitch_at
        self._glitch_deg = glitch_deg
        self._glitch_for = glitch_for
        self._glitch_state = "pending" if glitch_at is not None else "off"

    def observe(self, message: Any) -> None:
        kind = message.get_type()
        if (
            kind == "HEARTBEAT"
            and message.get_srcSystem() == 1
            and message.type != mavlink2.MAV_TYPE_GCS
        ):
            self._armed = bool(message.base_mode & _ARMED_FLAG)
            self._mode = int(message.custom_mode)
        elif kind == "GLOBAL_POSITION_INT":
            self._rel_alt = message.relative_alt / 1000.0
            if self._home is None and (message.lat or message.lon):
                self._home = (message.lat / 1e7, message.lon / 1e7)

    def _command(self, command: int, *params: float) -> bytes:
        values = list(params) + [0.0] * (7 - len(params))
        return bytes(self._mav.command_long_encode(1, 1, command, 0, *values).pack(self._mav))

    def _param(self, name: str, value: float) -> bytes:
        return bytes(
            self._mav.param_set_encode(
                1, 1, name.encode(), value, mavlink2.MAV_PARAM_TYPE_REAL32
            ).pack(self._mav)
        )

    def _target(self, lat: float, lon: float) -> bytes:
        return bytes(
            self._mav.set_position_target_global_int_encode(
                0,
                1,
                1,
                mavlink2.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                _POSITION_ONLY_MASK,
                int(lat * 1e7),
                int(lon * 1e7),
                _CRUISE_ALT_M,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ).pack(self._mav)
        )

    def _set(self, state: str) -> None:
        self.state = state
        _log(f"state: {state}")

    def step(self, now: float) -> list[bytes]:
        """Return the frames to send now."""
        out: list[bytes] = []
        due = now - self._last_command >= 2.0
        if self.state == "wait_position" and self._home is not None:
            self._set("guided")
        elif self.state == "guided":
            if self._mode == _GUIDED:
                self._set("arming")
            elif due:
                out.append(self._command(mavlink2.MAV_CMD_DO_SET_MODE, 1, _GUIDED))
        elif self.state == "arming":
            if self._armed:
                self._set("takeoff")
                self._last_command = 0.0
                due = True
            elif due:
                out.append(self._command(mavlink2.MAV_CMD_COMPONENT_ARM_DISARM, 1))
        if self.state == "takeoff":
            if self._rel_alt >= _CRUISE_ALT_M * 0.85:
                self._set("cruise")
                self._cruise_start = now
            elif due:
                out.append(self._command(mavlink2.MAV_CMD_NAV_TAKEOFF, *([0.0] * 6), _CRUISE_ALT_M))
        if self.state == "cruise" and self._home is not None and now - self._last_command >= 1.0:
            leg = int((now - self._cruise_start) // _LEG_SECONDS) % len(_SQUARE_DEG)
            dlat, dlon = _SQUARE_DEG[(leg + 1) % len(_SQUARE_DEG)]
            out.append(self._target(self._home[0] + dlat, self._home[1] + dlon))
            out.extend(self._glitch(now - self._cruise_start))
        if out:
            self._last_command = now
        return out

    def _glitch(self, elapsed: float) -> list[bytes]:
        if self._glitch_at is None:
            return []
        if self._glitch_state == "pending" and elapsed >= self._glitch_at:
            self._glitch_state = "active"
            _log(f"GPS glitch on: +{self._glitch_deg} deg latitude")
        elif self._glitch_state == "active" and elapsed >= self._glitch_at + self._glitch_for:
            self._glitch_state = "done"
            _log("GPS glitch off")
        if self._glitch_state == "active":
            return [self._param("SIM_GPS_GLITCH_X", self._glitch_deg)]
        if self._glitch_state == "done":
            self._glitch_state = "cleared"
            return [self._param("SIM_GPS_GLITCH_X", 0.0)]
        return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tcp", default="127.0.0.1:5760")
    parser.add_argument("--udp", default="127.0.0.1:14550")
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--rate-hz", type=float, default=10.0)
    parser.add_argument("--fly", action="store_true", help="take off and fly a square circuit")
    parser.add_argument("--glitch-at", type=float, default=None, help="seconds into the circuit")
    parser.add_argument("--glitch-deg", type=float, default=0.003, help="latitude offset")
    parser.add_argument("--glitch-for", type=float, default=15.0, help="glitch duration, seconds")
    args = parser.parse_args()
    if args.glitch_at is not None and not args.fly:
        parser.error("--glitch-at requires --fly")

    mav = mavlink2.MAVLink(None, srcSystem=255, srcComponent=190)
    rx = mavlink2.MAVLink(None)
    rx.robust_parsing = True
    pilot = Pilot(mav, args.glitch_at, args.glitch_deg, args.glitch_for) if args.fly else None
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_target = _split(args.udp)
    deadline = time.monotonic() + args.seconds
    delivered = 0
    dropped = 0
    interval_us = float(int(1_000_000 / args.rate_hz))
    with _connect(_split(args.tcp), deadline) as tcp:
        tcp.settimeout(0.5)
        heartbeat = bytes(
            mav.heartbeat_encode(
                mavlink2.MAV_TYPE_GCS, mavlink2.MAV_AUTOPILOT_INVALID, 0, 0, 0
            ).pack(mav)
        )
        streams = [
            bytes(
                mav.command_long_encode(
                    1,
                    1,
                    mavlink2.MAV_CMD_SET_MESSAGE_INTERVAL,
                    0,
                    message_id,
                    interval_us,
                    0,
                    0,
                    0,
                    0,
                    0,
                ).pack(mav)
            )
            for message_id in (_GLOBAL_POSITION_INT, _GPS_RAW_INT)
        ]
        last_heartbeat = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - last_heartbeat > 1.0:
                tcp.sendall(heartbeat + b"".join(streams))
                last_heartbeat = now
            if pilot is not None:
                for frame in pilot.step(now):
                    tcp.sendall(frame)
            try:
                data = tcp.recv(4096)
            except TimeoutError:
                continue
            if not data:
                break
            if pilot is not None:
                for message in rx.parse_buffer(data) or []:
                    pilot.observe(message)
            if try_send(udp, data, udp_target):
                delivered += 1
            else:
                dropped += 1
    if pilot is not None:
        _log(f"final state: {pilot.state}")
    _log(f"relayed {delivered} datagrams, dropped {dropped}")
    return 0 if delivered else 1


if __name__ == "__main__":
    raise SystemExit(main())
