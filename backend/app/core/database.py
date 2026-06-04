"""Database engine, session factory, and the declarative base.

There is exactly one engine factory here. The dialect is chosen by the
``DATABASE_URL`` (SQLite locally, PostgreSQL in production) — nothing branches on
an environment name. SQLite connections get WAL mode (concurrent reads) and
enforced foreign keys, applied only when the dialect is SQLite.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models (SQLAlchemy 2.0 ``Mapped`` style)."""


def _enable_sqlite_pragmas(dbapi_connection: object, _: object) -> None:
    """Turn on WAL journaling and foreign-key enforcement for a SQLite connection.

    WAL gives concurrent readers while a writer is active; foreign keys are off by
    default in SQLite and must be enabled per connection. No-op for other dialects
    because this listener is only registered for SQLite engines.
    """
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(database_url: str) -> Engine:
    """Create the SQLAlchemy engine for the given URL.

    Applies SQLite-specific connection arguments and pragmas when the URL is
    SQLite, and leaves PostgreSQL (or any other dialect) with framework defaults.

    Args:
        database_url: A SQLAlchemy connection URL; its dialect selects the driver.

    Returns:
        A configured ``Engine`` ready to bind a session factory.
    """
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(database_url, connect_args=connect_args, future=True)
    if is_sqlite:
        event.listen(engine, "connect", _enable_sqlite_pragmas)
    return engine


engine = create_db_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Yield a request-scoped database session, closing it afterward.

    FastAPI dependency. The session is closed in a ``finally`` so connections are
    always returned to the pool. Transactions are owned by the service layer, not
    here — this only manages the session lifecycle.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
