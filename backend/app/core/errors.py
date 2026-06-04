"""Typed application errors and the single error envelope they serialize to.

Every error the API returns shares one shape::

    { "error": { "code": "employee.not_found", "message": "...", "details": {} } }

``code`` is a stable, machine-readable string; the HTTP status carries the class.
Services raise these typed exceptions; a handful of exception handlers (registered
in ``main``) map them to the envelope. Raw exceptions never reach the client.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.pagination import InvalidCursorError

logger = get_logger(__name__)


class ErrorBody(BaseModel):
    """The inner error object of the standard envelope."""

    code: str = Field(description="Stable, machine-readable error code.")
    message: str = Field(description="Human-readable explanation, safe to display.")
    details: dict[str, object] = Field(
        default_factory=dict, description="Optional structured context for the error."
    )


class ErrorEnvelope(BaseModel):
    """The standard error response wrapper returned by every failing endpoint."""

    error: ErrorBody


class AppError(Exception):
    """Base class for expected, typed application errors.

    Carries a stable ``code``, an HTTP ``status_code``, and optional ``details``.
    Subclasses fix the code and status so call sites raise intent, not plumbing.

    Attributes:
        code: Stable machine-readable identifier (e.g. ``employee.not_found``).
        message: Safe, human-readable message.
        status_code: HTTP status that classifies the error.
        details: Optional structured context included in the envelope.
    """

    code: str = "internal.error"
    status_code: int = 500

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_envelope(self) -> ErrorEnvelope:
        """Render this error as the standard response envelope."""
        body = ErrorBody(code=self.code, message=self.message, details=self.details)
        return ErrorEnvelope(error=body)


class NotFoundError(AppError):
    """A requested resource does not exist (or is soft-deleted)."""

    code = "resource.not_found"
    status_code = 404


class EmployeeNotFoundError(NotFoundError):
    """The requested employee does not exist."""

    code = "employee.not_found"


class ConflictError(AppError):
    """The request conflicts with current state (e.g. a duplicate unique field)."""

    code = "resource.conflict"
    status_code = 409


class ValidationError(AppError):
    """A business-rule validation failed (distinct from request-schema validation)."""

    code = "request.invalid"
    status_code = 422


class QaUnavailableError(AppError):
    """The natural-language Q&A could not produce a safe answer."""

    code = "qa.unavailable"
    status_code = 422


async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    """Map a typed :class:`AppError` to its envelope and HTTP status."""
    return JSONResponse(status_code=exc.status_code, content=exc.to_envelope().model_dump())


async def handle_request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Map FastAPI's request-schema validation failure to the standard envelope.

    Only the location, message, and type of each error are surfaced. The raw
    ``ctx`` is dropped because it can contain non-serializable exception objects
    and internal detail we never want to leak to the client.
    """
    sanitized = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    body = ErrorBody(
        code="request.invalid",
        message="The request body or parameters failed validation.",
        details={"errors": sanitized},
    )
    return JSONResponse(status_code=422, content=ErrorEnvelope(error=body).model_dump())


async def handle_invalid_cursor_error(_: Request, exc: InvalidCursorError) -> JSONResponse:
    """Map a malformed pagination cursor to a 422 with a stable error code."""
    body = ErrorBody(code="pagination.invalid_cursor", message=str(exc))
    return JSONResponse(status_code=422, content=ErrorEnvelope(error=body).model_dump())


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions: log internally, return a generic envelope.

    Internal detail is logged with the request ID and stack trace; the client gets
    a generic 500 with no leaked internals.
    """
    logger.error("unhandled_exception", path=request.url.path, method=request.method, exc_info=exc)
    body = ErrorBody(code="internal.error", message="An unexpected error occurred.")
    return JSONResponse(status_code=500, content=ErrorEnvelope(error=body).model_dump())
