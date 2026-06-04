"""Unit tests for EmployeeService read paths using a fake repository.

These exercise the service's mapping and orchestration logic with an in-memory fake
repository and no database — fast and isolated. Write paths (which own a transaction)
are covered by the integration tests against real SQLite.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from app.core.errors import EmployeeNotFoundError
from app.domain.currency import Currency
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeFilters
from app.services.currency_converter import FxTableCurrencyConverter
from app.services.employee_service import EmployeeService

RATES = {"EUR": 1_080_000, "INR": 12_000}


def make_employee(**overrides: object) -> Employee:
    """Build an Employee ORM object (no DB) with sensible defaults for mapping tests."""
    defaults: dict[str, object] = {
        "id": 1,
        "employee_code": "EMP-00001",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@acme.test",
        "department": "Engineering",
        "job_title": "Staff Engineer",
        "level": "L5",
        "employment_type": "Full-time",
        "country": "US",
        "currency": "USD",
        "base_salary_minor": 180_000_00,
        "base_salary_usd_minor": 180_000_00,
        "hire_date": date(2020, 1, 1),
    }
    defaults.update(overrides)
    employee = Employee(**defaults)
    employee.created_at = datetime(2020, 1, 1, tzinfo=UTC)
    employee.updated_at = datetime(2020, 1, 2, tzinfo=UTC)
    return employee


class FakeEmployeeRepository:
    """In-memory stand-in honoring the reader and writer protocols (Liskov)."""

    def __init__(self, employees: list[Employee]) -> None:
        self._by_id = {employee.id: employee for employee in employees}
        self.next_cursor: str | None = None

    def get_by_id(self, employee_id: int) -> Employee | None:
        return self._by_id.get(employee_id)

    def get_by_email(self, email: str) -> Employee | None:
        return next((e for e in self._by_id.values() if e.email == email), None)

    def count(self, filters: EmployeeFilters) -> int:
        return len(self._by_id)

    def page(
        self,
        filters: EmployeeFilters,
        *,
        sort_by: str,
        sort_dir: str,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[Employee], str | None]:
        return list(self._by_id.values())[:limit], self.next_cursor

    def add(self, employee: Employee) -> None:
        self._by_id[employee.id] = employee

    def soft_delete(self, employee: Employee) -> None:
        del self._by_id[employee.id]


def make_service(employees: list[Employee]) -> tuple[EmployeeService, FakeEmployeeRepository]:
    repo = FakeEmployeeRepository(employees)
    converter = FxTableCurrencyConverter(RATES, Currency("USD"))
    service = EmployeeService(reader=repo, writer=repo, converter=converter, session=MagicMock())
    return service, repo


def test_get_employee_maps_local_and_usd_salary() -> None:
    employee = make_employee(
        country="DE", currency="EUR", base_salary_minor=100_000_00, base_salary_usd_minor=108_000_00
    )
    service, _ = make_service([employee])

    response = service.get_employee(1)

    assert response.base_salary.currency == "EUR"
    assert response.base_salary.amount == 100_000
    assert response.base_salary_usd.currency == "USD"
    assert response.base_salary_usd.minor_units == 108_000_00
    assert response.country_name == "Germany"


def test_get_missing_employee_raises_not_found() -> None:
    service, _ = make_service([])

    with pytest.raises(EmployeeNotFoundError):
        service.get_employee(999)


def test_list_employees_returns_total_and_cursor() -> None:
    service, repo = make_service(
        [
            make_employee(id=i, employee_code=f"EMP-{i:05d}", email=f"e{i}@acme.test")
            for i in range(1, 4)
        ]
    )
    repo.next_cursor = "more"

    page = service.list_employees(
        EmployeeFilters(), sort_by="id", sort_dir="asc", cursor=None, limit=2
    )

    assert page.total == 3
    assert page.next_cursor == "more"
    assert len(page.items) == 2
