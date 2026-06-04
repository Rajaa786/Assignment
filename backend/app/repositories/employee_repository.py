"""Data access for employees — the only layer that speaks SQLAlchemy for this entity.

Exposes two narrow protocols (``EmployeeReader``, ``EmployeeWriter``) so services
depend on exactly the capability they use (Interface Segregation). The SQL
implementation builds filtered, keyset-paginated queries; it never orchestrates
business rules or opens transactions — that is the service's job.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Protocol, TypeVar

from sqlalchemy import Select, and_, func, insert, or_, select
from sqlalchemy.orm import Session

from app.core.pagination import SortDirection, decode_cursor, encode_cursor
from app.models.employee import Employee

# The filter helper is reused by the row query and the count query, which have
# different result shapes; this constrained TypeVar keeps it precisely typed.
_FilterableSelect = TypeVar("_FilterableSelect", Select[tuple[Employee]], Select[tuple[int]])

# Sortable fields exposed to the API, mapped to their model column. Only stable,
# indexed columns are sortable; ``id`` is always the keyset tiebreaker.
SORTABLE_COLUMNS = {
    "id": Employee.id,
    "name": Employee.last_name,
    "salary": Employee.base_salary_usd_minor,
    "hire_date": Employee.hire_date,
}


@dataclass(frozen=True, slots=True)
class EmployeeFilters:
    """A set of optional filters applied to an employee list query.

    Attributes:
        search: Case-insensitive substring matched across name, email, and code.
        department: Exact department name.
        country: Exact ISO 3166 country code.
        level: Exact level code.
        salary_usd_min_minor: Inclusive lower bound on USD-normalized salary (minor units).
        salary_usd_max_minor: Inclusive upper bound on USD-normalized salary (minor units).
    """

    search: str | None = None
    department: str | None = None
    country: str | None = None
    level: str | None = None
    salary_usd_min_minor: int | None = None
    salary_usd_max_minor: int | None = None


class EmployeeReader(Protocol):
    """Read-side employee data access."""

    def get_by_id(self, employee_id: int) -> Employee | None: ...

    def get_by_email(self, email: str) -> Employee | None: ...

    def count(self, filters: EmployeeFilters) -> int: ...

    def page(
        self,
        filters: EmployeeFilters,
        *,
        sort_by: str,
        sort_dir: SortDirection,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[Employee], str | None]: ...


class EmployeeWriter(Protocol):
    """Write-side employee data access."""

    def add(self, employee: Employee) -> None: ...

    def soft_delete(self, employee: Employee) -> None: ...


def _sort_value_for_cursor(employee: Employee, sort_by: str) -> str | int:
    """Extract the value that seeds the next cursor for the given sort field."""
    if sort_by == "hire_date":
        return employee.hire_date.isoformat()
    if sort_by == "name":
        return employee.last_name
    if sort_by == "salary":
        return employee.base_salary_usd_minor
    return employee.id


def _cast_cursor_value(sort_by: str, value: str | int) -> str | int | date:
    """Cast a decoded cursor value back to the type its column compares against."""
    if sort_by == "hire_date":
        return date.fromisoformat(str(value))
    if sort_by == "name":
        return str(value)
    return int(value)


class SqlEmployeeRepository:
    """SQLAlchemy-backed :class:`EmployeeReader` and :class:`EmployeeWriter`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, employee_id: int) -> Employee | None:
        """Return the active (non-deleted) employee with this id, or ``None``."""
        stmt = select(Employee).where(Employee.id == employee_id, Employee.deleted_at.is_(None))
        return self._session.scalars(stmt).one_or_none()

    def get_by_email(self, email: str) -> Employee | None:
        """Return any employee with this email, including soft-deleted ones.

        Email is globally unique, so duplicate detection must see soft-deleted rows.
        """
        stmt = select(Employee).where(Employee.email == email)
        return self._session.scalars(stmt).one_or_none()

    def add(self, employee: Employee) -> None:
        """Stage a new employee for insertion (no commit — the service owns that)."""
        self._session.add(employee)

    def max_id(self) -> int:
        """Return the largest employee id in the table, or 0 if empty.

        Used by bulk import to pre-allocate ``EMP-`` codes for inserted rows. Safe
        for the single-writer profile of this tool (one HR manager).
        """
        return self._session.scalar(select(func.coalesce(func.max(Employee.id), 0))) or 0

    def bulk_insert(self, rows: list[dict[str, object]]) -> None:
        """Insert many employees in a single statement (no commit).

        Uses a Core ``insert`` executemany rather than per-row ``add`` so large CSV
        imports and the 10k seed stay fast (``CLAUDE.md`` §6).
        """
        if rows:
            self._session.execute(insert(Employee), rows)

    def iter_filtered(self, filters: EmployeeFilters) -> Iterator[Employee]:
        """Stream all active employees matching the filters, ordered by id.

        Streams with ``yield_per`` so CSV export of the full dataset never loads
        every row into memory at once.
        """
        stmt = select(Employee).where(Employee.deleted_at.is_(None))
        stmt = self._apply_filters(stmt, filters).order_by(Employee.id.asc())
        yield from self._session.scalars(stmt).yield_per(500)

    def soft_delete(self, employee: Employee) -> None:
        """Mark an employee as deleted by stamping ``deleted_at`` (no commit)."""
        employee.deleted_at = func.now()

    def count(self, filters: EmployeeFilters) -> int:
        """Return the number of active employees matching the filters."""
        stmt = select(func.count()).select_from(Employee).where(Employee.deleted_at.is_(None))
        stmt = self._apply_filters(stmt, filters)
        return self._session.scalar(stmt) or 0

    def page(
        self,
        filters: EmployeeFilters,
        *,
        sort_by: str,
        sort_dir: SortDirection,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[Employee], str | None]:
        """Return one keyset page of employees and the cursor for the next page.

        Fetches ``limit + 1`` rows to detect whether a further page exists without a
        second query, then returns at most ``limit`` rows and a next cursor (or
        ``None`` at the end).
        """
        column = SORTABLE_COLUMNS[sort_by]
        stmt = select(Employee).where(Employee.deleted_at.is_(None))
        stmt = self._apply_filters(stmt, filters)

        if cursor is not None:
            raw_value, last_id = decode_cursor(cursor)
            keyset_value = _cast_cursor_value(sort_by, raw_value)
            if sort_dir == "asc":
                stmt = stmt.where(
                    or_(column > keyset_value, and_(column == keyset_value, Employee.id > last_id))
                )
            else:
                stmt = stmt.where(
                    or_(column < keyset_value, and_(column == keyset_value, Employee.id < last_id))
                )

        direction = (
            (column.asc(), Employee.id.asc())
            if sort_dir == "asc"
            else (
                column.desc(),
                Employee.id.desc(),
            )
        )
        stmt = stmt.order_by(*direction).limit(limit + 1)

        rows = list(self._session.scalars(stmt).all())
        has_next = len(rows) > limit
        rows = rows[:limit]
        next_cursor = (
            encode_cursor(_sort_value_for_cursor(rows[-1], sort_by), rows[-1].id)
            if has_next and rows
            else None
        )
        return rows, next_cursor

    def _apply_filters(
        self, stmt: _FilterableSelect, filters: EmployeeFilters
    ) -> _FilterableSelect:
        """Apply the optional filters to a select statement."""
        if filters.search:
            needle = f"%{filters.search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Employee.first_name).like(needle),
                    func.lower(Employee.last_name).like(needle),
                    func.lower(Employee.email).like(needle),
                    func.lower(Employee.employee_code).like(needle),
                )
            )
        if filters.department:
            stmt = stmt.where(Employee.department == filters.department)
        if filters.country:
            stmt = stmt.where(Employee.country == filters.country)
        if filters.level:
            stmt = stmt.where(Employee.level == filters.level)
        if filters.salary_usd_min_minor is not None:
            stmt = stmt.where(Employee.base_salary_usd_minor >= filters.salary_usd_min_minor)
        if filters.salary_usd_max_minor is not None:
            stmt = stmt.where(Employee.base_salary_usd_minor <= filters.salary_usd_max_minor)
        return stmt
