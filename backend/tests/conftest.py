"""Shared pytest fixtures.

Every test runs against an isolated in-memory SQLite database created fresh per
test, with the ``get_session`` dependency overridden to use it. No file is touched,
no network is reached, and tests cannot bleed state into one another.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_session
from app.main import app


@pytest.fixture
def db_engine() -> Iterator[Engine]:
    """Create a fresh in-memory SQLite engine with the full schema."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)  # create_all is permitted in test fixtures only
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """Yield a session bound to the in-memory test engine."""
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine: Engine) -> Iterator[TestClient]:
    """Yield a TestClient whose sessions use the in-memory test engine."""
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    def override_get_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
