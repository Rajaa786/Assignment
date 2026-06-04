"""Rate limiting for abuse-prone endpoints (the LLM Q&A in particular).

The NL Q&A endpoint calls a paid model and runs generated SQL, so it is the one place
worth rate limiting (``CLAUDE.md`` §8). We use slowapi keyed by client IP; the limit is
applied per-endpoint via a decorator and exceeded requests are mapped to the standard
error envelope.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.errors import ErrorBody, ErrorEnvelope

limiter = Limiter(key_func=get_remote_address)

LLM_RATE_LIMIT = "10/minute"


def handle_rate_limit_exceeded(_: Request, __: Exception) -> JSONResponse:
    """Map a slowapi RateLimitExceeded to the standard 429 error envelope."""
    body = ErrorBody(
        code="rate_limited",
        message="Too many requests. Please wait a moment and try again.",
    )
    return JSONResponse(status_code=429, content=ErrorEnvelope(error=body).model_dump())
