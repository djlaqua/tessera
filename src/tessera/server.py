"""HTTP service: sync endpoint (hub mode), live map and read API.

Security defaults: binds to loopback (CLI), no OpenAPI docs, request bodies capped,
strict security headers with a CSP that only allows this origin plus the tile host,
optional bearer token for read endpoints, generic error messages for auth failures.
"""

from __future__ import annotations

import hmac
from importlib import resources
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from tessera.live import live_features
from tessera.sync.batch import SyncBatch
from tessera.sync.errors import AuthError, SyncError
from tessera.sync.hub import Hub

MAX_SYNC_BODY_BYTES = 2 * 1024 * 1024
DEFAULT_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
DEFAULT_TILE_ATTRIBUTION = "&copy; OpenStreetMap contributors"
STATIC_DIR = Path(str(resources.files("tessera") / "ui" / "static"))


def _tile_origin(tile_url: str) -> str:
    parsed = urlparse(tile_url.replace("{s}", "a"))
    if parsed.scheme != "https" or not parsed.hostname:
        return ""
    return f"https://{parsed.hostname}"


class _SecurityHeaders(BaseHTTPMiddleware):
    def __init__(self, app: Any, tile_origin: str) -> None:
        super().__init__(app)
        img = f"'self' data: {tile_origin}".strip()
        self._csp = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            f"img-src {img}; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'none'"
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = self._csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response


async def _read_capped(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length")
    if declared is not None and (not declared.isdigit() or int(declared) > limit):
        raise HTTPException(status_code=413, detail="body too large")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            raise HTTPException(status_code=413, detail="body too large")
    return bytes(body)


def create_app(
    db_path: str | Path,
    *,
    hub: Hub | None = None,
    read_token: str | None = None,
    tile_url: str = DEFAULT_TILE_URL,
    tile_attribution: str = DEFAULT_TILE_ATTRIBUTION,
) -> FastAPI:
    """Build the app. With `hub`, `/v1/sync` accepts signed batches into the hub store."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(_SecurityHeaders, tile_origin=_tile_origin(tile_url))
    store_path = Path(db_path)

    def require_reader(request: Request) -> None:
        if read_token is None:
            return
        supplied = request.headers.get("authorization", "")
        expected = f"Bearer {read_token}"
        if not hmac.compare_digest(supplied.encode(), expected.encode()):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "hub" if hub is not None else "edge"}

    @app.get("/v1/config")
    def config() -> dict[str, Any]:
        return {
            "tile_url": tile_url,
            "tile_attribution": tile_attribution,
            "auth_required": read_token is not None,
        }

    @app.get("/v1/features", dependencies=[Depends(require_reader)])
    def features(
        window: Annotated[int, Query(ge=1, le=20_000)] = 2_000,
        trail: Annotated[int, Query(ge=0, le=500)] = 50,
    ) -> dict[str, Any]:
        if not store_path.exists():
            return {"type": "FeatureCollection", "features": [], "skipped_rows": 0}
        return live_features(store_path, window=window, trail=trail)

    if hub is not None:

        @app.post("/v1/sync")
        async def sync(request: Request) -> JSONResponse:
            body = await _read_capped(request, MAX_SYNC_BODY_BYTES)
            try:
                batch = SyncBatch.model_validate_json(body)
                ack = await run_in_threadpool(hub.receive, batch)
            except ValidationError as exc:
                raise HTTPException(status_code=400, detail="malformed batch") from exc
            except AuthError as exc:
                raise HTTPException(status_code=401, detail="unauthorized") from exc
            except SyncError as exc:
                raise HTTPException(status_code=400, detail="invalid batch") from exc
            return JSONResponse(ack.model_dump())

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
