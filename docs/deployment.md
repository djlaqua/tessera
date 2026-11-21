# Deployment

## Demo (one machine, Docker)
```bash
docker compose -f docker-compose.demo.yml up --build -d   # first build compiles SITL, about 6 to 15 min
open http://127.0.0.1:8080
docker compose -f docker-compose.demo.yml logs -f relay   # flight and glitch events
docker compose -f docker-compose.demo.yml down -v         # stop and delete demo data
```
The demo uses plain HTTP on an isolated Docker network and creates a key on first start.

## Edge and hub on real machines
1. Install on each machine (Python 3.11+): `python3.12 -m venv /opt/tessera/venv && /opt/tessera/venv/bin/pip install "tessera[server] @ git+https://github.com/djlaqua/tessera"`.
2. Create a service user: `useradd --system --home /var/lib/tessera tessera`.
3. On the edge: `tessera keygen --out /etc/tessera/edge-1.key`, then `chown tessera /etc/tessera/edge-1.key`.
4. Copy only `edge-1.key.pub` to the hub as `/etc/tessera/trusted/edge-1.pub`.
5. Put the hub behind TLS: either `--tls-cert/--tls-key`, or a reverse proxy (Caddy or nginx) on 443 forwarding to 127.0.0.1:8080.
6. Optional read token: `/etc/tessera/hub.env` with `TESSERA_READ_TOKEN=<long random value>`, mode 600. Open the map as `https://hub/#token=<value>`.
7. Install units from `deploy/systemd/`, edit hub URL and edge id, then `systemctl enable --now tessera-ingest tessera-sync` (edge) or `tessera-hub` (hub).

## Checks
- `curl https://hub/healthz` returns `{"status":"ok","mode":"hub"}`.
- `tessera sync --once ...` prints `synced N events`.
- `tessera integrity --db /var/lib/tessera/edge.db` lists flagged fixes.

## Security notes
- Never copy private keys to the hub. Rotate a key by adding the new `.pub`, switching the edge, then removing the old file.
- Ingest binds to loopback by default. Use MAVLink signing (`--signing-key-file`) on radio links.
- Back up `hub.db` with `sqlite3 hub.db ".backup hub-backup.db"`; edges resend anything the restored hub lacks.
