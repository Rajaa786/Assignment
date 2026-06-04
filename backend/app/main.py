"""FastAPI application factory and wiring.

Builds the app: structured logging, request-ID middleware, a strict CORS allowlist,
the standard error-envelope handlers, and the API routers under ``/api/v1``. The
module-level :data:`app` is what ASGI servers import (``app.main:app``).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api import employees, health
from app.core.config import settings
from app.core.errors import (
    AppError,
    handle_app_error,
    handle_invalid_cursor_error,
    handle_request_validation_error,
    handle_unexpected_error,
)
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.core.pagination import InvalidCursorError

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully wired ``FastAPI`` instance with logging, middleware, error
        handlers, and routers registered.
    """
    configure_logging()

    app = FastAPI(
        title="ACME Salary Management API",
        version="0.1.0",
        description=(
            "Internal API for managing employee salaries across countries and "
            "answering questions about how the organization pays people."
        ),
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    app.add_exception_handler(AppError, handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(InvalidCursorError, handle_invalid_cursor_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, handle_unexpected_error)

    app.include_router(health.router)
    app.include_router(employees.router, prefix=API_PREFIX)

    return app


app = create_app()
