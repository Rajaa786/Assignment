"""Container startup bootstrap: optionally seed an empty database.

Run as ``python -m app.seed.bootstrap`` between ``alembic upgrade head`` and starting
the server (see the Dockerfile). When ``SEED_ON_STARTUP`` is true it seeds 10k employees
only if the database is empty, so a freshly started container is immediately usable while
restarts never wipe existing data. When the flag is off it is a quiet no-op.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging, get_logger
from app.seed.seed import seed_if_empty

logger = get_logger(__name__)


def main() -> None:
    """Seed the database on startup if configured and currently empty."""
    configure_logging()
    if not settings.seed_on_startup:
        logger.info("seed_on_startup_disabled")
        return

    session = SessionLocal()
    try:
        inserted = seed_if_empty(session)
        if inserted:
            logger.info("startup_seed_complete", employees=inserted)
        else:
            logger.info("startup_seed_skipped_database_not_empty")
    finally:
        session.close()


if __name__ == "__main__":
    main()
