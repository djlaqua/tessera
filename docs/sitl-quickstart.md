# ArduPilot SITL quickstart

Verified on 2026-11-20 against ArduCopter SITL built from ArduPilot master (Linux, `./waf configure --board sitl && ./waf copter`, about 16 minutes on one core).

1. Build SITL: clone ArduPilot with submodules, then `./waf configure --board sitl && ./waf copter`. Container route: see ADR-006 (untested).
2. Start the simulator (no MAVProxy needed):
   `build/sitl/bin/arducopter --model + --speedup 1 --home 48.137,11.575,520,0 --defaults Tools/autotest/default_params/copter.parm --sim-address=127.0.0.1 -I0`
   It listens for MAVLink on TCP 5760.
3. Start ingest (loopback UDP):
   `tessera ingest-mavlink --db flight.db --port 14550 --max-events 200 --idle-timeout 30`
4. Relay TCP to UDP and request position at 10 Hz:
   `python scripts/sitl_relay.py --tcp 127.0.0.1:5760 --udp 127.0.0.1:14550 --seconds 40`
5. Replay: `tessera replay --db flight.db --format geojson > flight.geojson` (or `--format cot`).

Observed result: 200 observations, one entity (`sys1.comp1`), 10 Hz boot-time steps, position at the configured home, altitude tagged MSL (so CoT `hae` is unknown by design, ADR-004). The vehicle was stationary, so speed was 0.

Notes:
- Start the simulator and the relay in the same session. Do not kill processes with `pkill -f` patterns that match your own shell command.
- A 40 frame capture is committed as `tests/fixtures/sitl_global_position_int.bin` (synthetic data).
- Security: ingest binds to loopback by default. Use signing (`--signing-key-file`) on any real link.
