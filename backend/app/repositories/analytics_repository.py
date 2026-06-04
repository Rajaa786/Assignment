"""Data access for analytics.

Analytics needs only four fields per active employee — the grouping dimensions and the
USD-normalized salary. This repository fetches exactly those, once, so the service can
compute every metric in memory. It deliberately does not aggregate in SQL: the grouping
logic and the median/percentile math live in pure, unit-tested service functions, and at
10k rows the single projected scan is well within budget (see docs/performance.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee


@dataclass(frozen=True, slots=True)
class SalaryRow:
    """One active employee's grouping attributes and USD-normalized salary."""

    department: str
    country: str
    level: str
    usd_minor: int


class AnalyticsReader(Protocol):
    """Reads the minimal projection analytics needs."""

    def active_salary_rows(self) -> list[SalaryRow]:
        """Return one row per active employee with dimensions and USD salary."""
        ...


class SqlAnalyticsRepository:
    """SQLAlchemy-backed :class:`AnalyticsReader`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def active_salary_rows(self) -> list[SalaryRow]:
        """Project active employees to (department, country, level, USD salary)."""
        stmt = select(
            Employee.department,
            Employee.country,
            Employee.level,
            Employee.base_salary_usd_minor,
        ).where(Employee.deleted_at.is_(None))
        return [
            SalaryRow(department=row[0], country=row[1], level=row[2], usd_minor=row[3])
            for row in self._session.execute(stmt).all()
        ]
