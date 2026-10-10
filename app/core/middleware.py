"""HTTP middleware.

Currently holds request correlation. Kept separate from ``main.py`` so the
application factory stays a thin wiring layer.

Implemented as pure ASGI rather than on top of ``BaseHTTPMiddleware``: the
latter runs the downstream app in an extra task per request, which complicates
streaming responses and background tasks. A pure ASGI middleware wraps ``send``
directly, so headers are stamped on the response without buffering it.
"""

from __future__ import annotations

import time

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import (
    REQUEST_ID_HEADER,
    get_logger,
    new_request_id,
    reset_request_id,
    set_request_id,
)

logger = get_logger(__name__)

#: Guard against a client sending an oversized or hostile header value.
_MAX_INBOUND_REQUEST_ID_LEN = 128

_RESPONSE_TIME_HEADER = "X-Response-Time-ms"


class RequestContextMiddleware:
    """Attach a correlation ID to every request and echo it back.

    An inbound ``X-Request-ID`` is reused when it looks sane, so a trace
    started by a gateway or frontend survives into our logs. Otherwise a new
    one is generated.

    The ID is published in two places:

    - ``request.state.request_id`` - for endpoints and dependencies
    - a context variable - read by the log filter and the error handlers

    It is returned to the client in the ``X-Request-ID`` response header.
    """

    def __init__(self, app: ASGIApp, *, log_requests: bool = True) -> None:
        self.app = app
        self._log_requests = log_requests

    @staticmethod
    def _sanitize(value: str | None) -> str | None:
        """Accept an inbound ID only if it is safe to echo into a log/header."""
        if not value:
            return None
        candidate = value.strip()
        if not candidate or len(candidate) > _MAX_INBOUND_REQUEST_ID_LEN:
            return None
        if not all(ch.isalnum() or ch in "-_." for ch in candidate):
            return None
        return candidate

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Lifespan and websocket scopes carry no request to correlate.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        inbound = Headers(scope=scope).get(REQUEST_ID_HEADER)
        request_id = self._sanitize(inbound) or new_request_id()

        # ``Request.state`` is backed by scope["state"].
        scope.setdefault("state", {})["request_id"] = request_id

        token = set_request_id(request_id)
        started = time.perf_counter()
        status_code = 0

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                elapsed_ms = (time.perf_counter() - started) * 1000
                headers = MutableHeaders(raw=message.setdefault("headers", []))
                headers[REQUEST_ID_HEADER] = request_id
                headers[_RESPONSE_TIME_HEADER] = f"{elapsed_ms:.2f}"
            await send(message)

        method = scope.get("method", "-")
        path = scope.get("path", "-")

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            # The registered exception handlers build the client response;
            # this records the timing and correlation ID either way. No
            # exception text is logged here - `logger.exception` in the
            # handler owns the traceback.
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.error("%s %s raised after %.2fms", method, path, elapsed_ms)
            raise
        else:
            if self._log_requests:
                elapsed_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "%s %s -> %s in %.2fms", method, path, status_code, elapsed_ms
                )
        finally:
            # Reset last: the log calls above must still see the ID.
            reset_request_id(token)
