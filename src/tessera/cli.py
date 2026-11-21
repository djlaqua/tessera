"""Command line interface.

Commands: ingest, ingest-mavlink, replay, integrity, keygen, sync, hub, map, version.
Server and sync commands need the `server` or `sync` extras (`pip install "tessera[server]"`).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
from collections.abc import Callable, Iterator, Sequence
from importlib.metadata import version as package_version
from pathlib import Path
from types import FrameType
from typing import Any

from tessera.adapters.ais import AisAdapter
from tessera.adapters.base import Adapter
from tessera.adapters.mavlink import SIGNING_KEY_BYTES, MavlinkAdapter
from tessera.adapters.mqtt_json import MqttJsonAdapter
from tessera.encoders import to_cot, to_geojson_feature
from tessera.eventlog import EventLog
from tessera.ingest import bind_udp, ingest_socket
from tessera.models import Observation
from tessera.replay import Replayer

_EDGE_ID = re.compile(r"^[A-Za-z0-9._:\-]{1,64}$")


def _add_ingest_args(parser: argparse.ArgumentParser, *, default_port: int) -> None:
    parser.add_argument("--db", required=True, help="event log path")
    parser.add_argument("--bind", default="127.0.0.1", help="bind address (default: loopback)")
    parser.add_argument("--port", type=int, default=default_port)
    parser.add_argument("--source-id", default=None, help="defaults to <protocol>-udp")
    parser.add_argument("--max-events", type=int, default=None)
    parser.add_argument("--idle-timeout", type=float, default=None, help="seconds")
    parser.add_argument(
        "--signing-key-file",
        default=None,
        help="MAVLink only: file with the 32 byte signing key; enables signature enforcement",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tessera")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="store telemetry received over UDP")
    ingest.add_argument("--protocol", choices=("mavlink", "ais", "json"), required=True)
    _add_ingest_args(ingest, default_port=14550)

    legacy = sub.add_parser("ingest-mavlink", help="alias for: ingest --protocol mavlink")
    _add_ingest_args(legacy, default_port=14550)

    replay = sub.add_parser("replay", help="replay a log to stdout")
    replay.add_argument("--db", required=True)
    replay.add_argument("--format", choices=("cot", "geojson"), default="geojson")
    replay.add_argument("--speed", type=float, default=0.0, help="0 = as fast as possible")

    integrity = sub.add_parser("integrity", help="score position integrity of a log")
    integrity.add_argument("--db", required=True)
    integrity.add_argument("--all", action="store_true", help="print every fix, not only flagged")

    keygen = sub.add_parser("keygen", help="create an Ed25519 key pair for sync")
    keygen.add_argument("--out", required=True, help="private key path; public key gets .pub")

    sync = sub.add_parser("sync", help="send the event log to a hub")
    sync.add_argument("--db", required=True)
    sync.add_argument("--hub-url", required=True)
    sync.add_argument("--edge-id", required=True)
    sync.add_argument("--key", required=True, help="private key from `tessera keygen`")
    sync.add_argument("--ca-file", default=None, help="CA bundle for a private hub certificate")
    sync.add_argument("--once", action="store_true", help="drain once and exit")
    sync.add_argument("--interval", type=float, default=5.0, help="seconds between drains")
    sync.add_argument(
        "--allow-insecure-http",
        action="store_true",
        help="allow plain HTTP to a non-loopback hub (isolated networks only)",
    )

    for name, help_text in (
        ("hub", "run the sync hub with the live map"),
        ("map", "serve the live map for a local log"),
    ):
        server = sub.add_parser(name, help=help_text)
        server.add_argument("--db", required=True)
        server.add_argument("--host", default="127.0.0.1")
        server.add_argument("--port", type=int, default=8080)
        server.add_argument("--tile-url", default=None, help="https tile URL template")
        server.add_argument("--tls-cert", default=None)
        server.add_argument("--tls-key", default=None)
        if name == "hub":
            server.add_argument(
                "--trusted-keys", required=True, help="directory of <edge_id>.pub files"
            )

    sub.add_parser("version", help="print the version")
    return parser


def _adapter(protocol: str, source_id: str | None, signing_key_file: str | None) -> Adapter:
    source = source_id or f"{protocol}-udp"
    if protocol == "mavlink":
        key = Path(signing_key_file).read_bytes() if signing_key_file else None
        if key is not None and len(key) != SIGNING_KEY_BYTES:
            raise SystemExit(f"signing key must be exactly {SIGNING_KEY_BYTES} bytes")
        return MavlinkAdapter(source, signing_key=key)
    if signing_key_file:
        raise SystemExit("--signing-key-file only applies to --protocol mavlink")
    if protocol == "ais":
        return AisAdapter(source)
    return MqttJsonAdapter(source)


def _cmd_ingest(args: argparse.Namespace, protocol: str) -> int:
    adapter = _adapter(protocol, args.source_id, args.signing_key_file)
    with EventLog(args.db) as log, bind_udp(args.bind, args.port) as sock:
        stored = ingest_socket(
            sock, log, adapter, max_events=args.max_events, idle_timeout_s=args.idle_timeout
        )
    rejected = getattr(adapter, "rejected", 0)
    print(f"stored {stored} observations, rejected {rejected}", file=sys.stderr)
    return 0


def _write_lines(lines: Iterator[str]) -> int:
    try:
        for line in lines:
            sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        # Reader closed early (for example `| head`). Silence the flush at interpreter exit.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    with EventLog(args.db) as log:
        observations = iter(Replayer(log, speed=args.speed))
        if args.format == "cot":
            return _write_lines(
                to_cot(o).decode("utf-8") for o in observations if o.position is not None
            )

        def geojson() -> Iterator[str]:
            # Streamed FeatureCollection so large logs never load into memory.
            yield '{"type": "FeatureCollection", "features": ['
            first = True
            for observation in observations:
                if observation.position is None:
                    continue
                prefix = "" if first else ","
                first = False
                yield prefix + json.dumps(to_geojson_feature(observation))
            yield "]}"

        return _write_lines(geojson())


def _cmd_integrity(args: argparse.Namespace) -> int:
    from collections import defaultdict

    from tessera.integrity import score_track

    tracks: dict[tuple[str, str], list[Observation]] = defaultdict(list)
    with EventLog(args.db) as log:
        for _, observation in log.read():
            tracks[(observation.source_id, observation.entity_id)].append(observation)
    total = flagged = 0
    lines: list[str] = []
    for (source_id, entity_id), track in sorted(tracks.items()):
        by_id = {o.id: o for o in track}
        for result in score_track(track):
            total += 1
            if not result.trusted:
                flagged += 1
            if args.all or not result.trusted:
                observation = by_id[result.observation_id]
                lines.append(
                    json.dumps(
                        {
                            "source_id": source_id,
                            "entity_id": entity_id,
                            "observed_at": observation.observed_at.isoformat(),
                            "score": result.score,
                            "reasons": list(result.reasons),
                        }
                    )
                )
    print(f"scored {total} fixes, flagged {flagged}", file=sys.stderr)
    return _write_lines(iter(lines))


def _cmd_keygen(args: argparse.Namespace) -> int:
    from tessera.sync import signing

    private_path = Path(args.out)
    public_path = private_path.with_name(private_path.name + ".pub")
    if public_path.exists():
        raise SystemExit(f"{public_path} already exists")
    key = signing.generate_private_key()
    signing.save_private_key(key, private_path)
    signing.save_public_key(key.public_key(), public_path)
    print(f"private key: {private_path} (mode 600, keep secret)", file=sys.stderr)
    print(f"public key:  {public_path} (copy to the hub as <edge_id>.pub)", file=sys.stderr)
    return 0


def _stop_flag() -> Callable[[], bool]:
    state = {"stop": False}

    def handler(_signum: int, _frame: FrameType | None) -> None:
        state["stop"] = True

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    return lambda: state["stop"]


def _cmd_sync(args: argparse.Namespace) -> int:
    from tessera.sync import signing
    from tessera.sync.http import HttpTransport
    from tessera.sync.uplink import Uplink

    if not _EDGE_ID.match(args.edge_id):
        raise SystemExit("edge id must match [A-Za-z0-9._:-]{1,64}")
    transport = HttpTransport(
        args.hub_url, ca_file=args.ca_file, allow_insecure_http=args.allow_insecure_http
    )
    key = signing.load_private_key(Path(args.key))
    with EventLog(args.db) as log:
        uplink = Uplink(log, peer=args.hub_url, edge_id=args.edge_id, key=key, transport=transport)
        if args.once:
            sent = uplink.drain()
            print(
                f"synced {sent} events, hub cursor {log.get_cursor(args.hub_url)}", file=sys.stderr
            )
            return 0
        uplink.run(interval_s=args.interval, should_stop=_stop_flag())
    return 0


def _load_trusted_keys(directory: Path) -> dict[str, Any]:
    from tessera.sync import signing

    keys: dict[str, Any] = {}
    for path in sorted(directory.glob("*.pub")):
        edge_id = path.name[: -len(".pub")]
        if not _EDGE_ID.match(edge_id):
            raise SystemExit(f"invalid edge id in key file name: {path.name}")
        keys[edge_id] = signing.load_public_key(path)
    if not keys:
        raise SystemExit(f"no <edge_id>.pub files found in {directory}")
    return keys


def _cmd_serve(args: argparse.Namespace, *, hub_mode: bool) -> int:
    try:
        import uvicorn

        from tessera.server import DEFAULT_TILE_URL, create_app
    except ImportError as exc:
        raise SystemExit(
            'this command needs the server extra: pip install "tessera[server]"'
        ) from exc
    hub = None
    if hub_mode:
        from tessera.sync.hub import Hub, HubStore

        hub = Hub(HubStore(args.db), _load_trusted_keys(Path(args.trusted_keys)))
    app = create_app(
        args.db,
        hub=hub,
        read_token=os.environ.get("TESSERA_READ_TOKEN") or None,
        tile_url=args.tile_url or DEFAULT_TILE_URL,
    )
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        ssl_certfile=args.tls_cert,
        ssl_keyfile=args.tls_key,
        server_header=False,
        log_level="info",
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    command: str = args.command
    if command == "ingest":
        return _cmd_ingest(args, args.protocol)
    if command == "ingest-mavlink":
        return _cmd_ingest(args, "mavlink")
    if command == "replay":
        return _cmd_replay(args)
    if command == "integrity":
        return _cmd_integrity(args)
    if command == "keygen":
        return _cmd_keygen(args)
    if command == "sync":
        return _cmd_sync(args)
    if command in ("hub", "map"):
        return _cmd_serve(args, hub_mode=command == "hub")
    print(package_version("tessera"))
    return 0
