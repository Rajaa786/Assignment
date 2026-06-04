"""HTTP middleware: request-ID propagation.

Every request gets a stable ID (taken from an inbound ``X-Request-ID`` if present,
otherwise generated). The ID is bound into the structlog context so every log line
for the request carries it, and echoed back in the ``X-Request-ID`` response header
for client-side correlation.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Bind a request ID to the logging context and echo it on the response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Attach a request ID for the lifetime of the request.

        Args:
            request: The incoming request.
            call_next: The downstream ASGI handler.

        Returns:
            The downstream response with the ``X-Request-ID`` header set.
        """
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
