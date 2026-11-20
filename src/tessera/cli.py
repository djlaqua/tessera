"""Command line interface: `tessera ingest-mavlink` and `tessera replay`."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from tessera.adapters.mavlink import MavlinkAdapter
from tessera.encoders import to_cot, to_geojson
from tessera.eventlog import EventLog
from tessera.ingest import bind_udp, ingest_socket
from tessera.replay import Replayer


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tessera")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest-mavlink", help="store MAVLink 2 telemetry from UDP")
    ingest.add_argument("--db", required=True, help="event log path")
    ingest.add_argument("--bind", default="127.0.0.1", help="bind address (default: loopback)")
    ingest.add_argument("--port", type=int, default=14550)
    ingest.add_argument("--source-id", default="mavlink-udp")
    ingest.add_argument("--max-events", type=int, default=None)
    ingest.add_argument("--idle-timeout", type=float, default=None, help="seconds")

    replay = sub.add_parser("replay", help="replay a log to stdout")
    replay.add_argument("--db", required=True)
    replay.add_argument("--format", choices=("cot", "geojson"), default="geojson")
    replay.add_argument("--speed", type=float, default=0.0, help="0 = as fast as possible")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "ingest-mavlink":
        with EventLog(args.db) as log, bind_udp(args.bind, args.port) as sock:
            stored = ingest_socket(
                sock,
                log,
                MavlinkAdapter(args.source_id),
                max_events=args.max_events,
                idle_timeout_s=args.idle_timeout,
            )
        print(f"stored {stored} observations", file=sys.stderr)
        return 0
    with EventLog(args.db) as log:
        observations = list(Replayer(log, speed=args.speed))
    if args.format == "cot":
        for observation in observations:
            if observation.position is not None:
                sys.stdout.write(to_cot(observation).decode("utf-8") + "\n")
    else:
        sys.stdout.write(json.dumps(to_geojson(observations)) + "\n")
    return 0
