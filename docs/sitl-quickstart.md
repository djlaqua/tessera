# ArduPilot SITL quickstart

Goal: stream simulated telemetry into Tessera and replay it. Commands marked VERIFY depend on your ArduPilot version.

1. Install ArduPilot SITL (or use a container, see ADR-006). VERIFY against the ArduPilot docs.
2. Start a simulated copter that forwards MAVLink to UDP 14550, for example:
   `sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550` (VERIFY)
3. Ingest:
   `tessera ingest-mavlink --db flight.db --port 14550 --max-events 500`
4. Replay as GeoJSON or CoT:
   `tessera replay --db flight.db --format geojson > flight.geojson`
   `tessera replay --db flight.db --format cot`
5. Open `flight.geojson` in geojson.io or QGIS. Use synthetic data only for public demos.

Security: the ingest command binds to loopback by default. Do not expose the port without TLS or a signed link.
