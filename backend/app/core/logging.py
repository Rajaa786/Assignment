"""Structured logging setup.

Configures structlog once at startup: JSON output in production (machine-parseable)
and a colorized console renderer locally. The request-ID middleware binds a
``request_id`` into the context so every line emitted during a request carries it.

Policy: **salary amounts are never logged.** Log employee IDs and operations, not
compensation values (``CLAUDE.md`` §8).
"""

from __future__ import annotations

import logging
from typing import cast

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """Configure structlog and the stdlib logging bridge for the whole process.

    Idempotent enough to call once on app startup. Chooses a JSON renderer when
    ``LOG_FORMAT=json`` (production) and a human-readable console renderer
    otherwise. Honors ``LOG_LEVEL``.
    """
    logging.basicConfig(format="%(message)s", level=settings.log_level.upper())

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger.

    Args:
        name: Optional logger name, conventionally ``__name__`` of the caller.

    Returns:
        A bound logger that emits structured events with merged context.
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
