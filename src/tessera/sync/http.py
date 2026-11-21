"""HTTPS transport for the uplink (standard library only)."""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from urllib.parse import urlparse

from pydantic import ValidationError

from tessera.sync.batch import Ack, SyncBatch
from tessera.sync.errors import AuthError, SyncError, TransportError

MAX_ACK_BYTES = 4_096
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class HttpTransport:
    """POSTs batches to `<hub_url>/v1/sync`.

    Plain HTTP is refused except to loopback, unless `allow_insecure_http` is set (for an
    isolated container network). HTTPS requires TLS 1.3.
    """

    def __init__(
        self,
        hub_url: str,
        *,
        timeout_s: float = 15.0,
        ca_file: str | None = None,
        allow_insecure_http: bool = False,
    ) -> None:
        parsed = urlparse(hub_url)
        if parsed.scheme not in ("https", "http") or not parsed.hostname:
            raise ValueError("hub URL must be http(s)://host[:port]")
        if parsed.scheme == "http" and parsed.hostname not in _LOOPBACK and not allow_insecure_http:
            raise ValueError("refusing plain HTTP to a non-loopback hub; use https")
        self._url = hub_url.rstrip("/") + "/v1/sync"
        self._timeout = timeout_s
        self._context: ssl.SSLContext | None = None
        if parsed.scheme == "https":
            self._context = ssl.create_default_context(cafile=ca_file)
            self._context.minimum_version = ssl.TLSVersion.TLSv1_3

    def send(self, batch: SyncBatch) -> Ack:
        request = urllib.request.Request(  # noqa: S310 (scheme validated in __init__)
            self._url,
            data=batch.model_dump_json().encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(  # noqa: S310 (scheme validated in __init__)
                request, timeout=self._timeout, context=self._context
            ) as response:
                body = response.read(MAX_ACK_BYTES + 1)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise AuthError("hub rejected the batch signature or edge id") from exc
            if exc.code == 429 or exc.code >= 500:
                raise TransportError(f"hub unavailable (HTTP {exc.code})") from exc
            raise SyncError(f"hub rejected batch (HTTP {exc.code})") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransportError("hub unreachable") from exc
        if len(body) > MAX_ACK_BYTES:
            raise SyncError("acknowledgement too large")
        try:
            return Ack.model_validate_json(body)
        except ValidationError as exc:
            raise SyncError("malformed acknowledgement") from exc
