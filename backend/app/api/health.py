"""Liveness and readiness probes for the platform's routing checks.

``/healthz`` answers "is the process up?" with no dependencies. ``/readyz`` answers
"can this instance serve traffic?" — it must reach the database before returning 200,
so the platform stops routing to an instance that has lost its DB.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_session

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
def liveness() -> dict[str, Literal["ok"]]:
    """Return 200 if the process is alive. No dependencies are checked."""
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness probe")
def readiness(session: Session = Depends(get_session)) -> dict[str, str]:
    """Return 200 only if the database is reachable.

    Executes a trivial ``SELECT 1``. If the database is unreachable the query
    raises and the global handler returns a 500, which is the correct "not ready"
    signal for the platform.

    Note: a migrations-current check is added alongside the Alembic setup.
    """
    session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "reachable"}
