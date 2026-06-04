"""Unit tests for the CSV import/export service with a fake repository."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.core.errors import ValidationError
from app.domain.currency import Currency
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeFilters
from app.services.csv_service import EmployeeCsvService
from app.services.currency_converter import FxTableCurrencyConverter

HEADER = "first_name,last_name,email,department,job_title,level,employment_type,country,base_salary_amount,hire_date"  # noqa: E501


def csv_bytes(*rows: str) -> bytes:
    return ("\n".join([HEADER, *rows]) + "\n").encode("utf-8")


class FakeCsvRepository:
    def __init__(
        self, existing_emails: set[str] | None = None, employees: list[Employee] | None = None
    ) -> None:
        self._existing = existing_emails or set()
        self._employees = employees or []
        self.inserted: list[dict[str, object]] = []

    def get_by_email(self, email: str) -> Employee | None:
        return Employee(email=email) if email in self._existing else None

    def max_id(self) -> int:
        return 0

    def bulk_insert(self, rows: list[dict[str, object]]) -> None:
        self.inserted.extend(rows)

    def iter_filtered(self, filters: EmployeeFilters) -> Iterator[Employee]:
        yield from self._employees


def make_service(repo: FakeCsvRepository) -> EmployeeCsvService:
    converter = FxTableCurrencyConverter({"EUR": 1_080_000}, Currency("USD"))
    return EmployeeCsvService(repository=repo, converter=converter, session=MagicMock())


def test_import_inserts_all_valid_rows() -> None:
    repo = FakeCsvRepository()
    content = csv_bytes(
        "Ada,Lovelace,ada@acme.test,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01",
        "Alan,Turing,alan@acme.test,Engineering,Engineer,L5,Full-time,DE,150000.00,2020-02-02",
    )

    result = make_service(repo).import_employees(content, dry_run=False)

    assert result.inserted == 2
    assert result.failed == 0
    assert len(repo.inserted) == 2
    assert repo.inserted[0]["employee_code"] == "EMP-00001"


def test_dry_run_validates_without_inserting() -> None:
    repo = FakeCsvRepository()
    content = csv_bytes(
        "Ada,Lovelace,ada@acme.test,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01"
    )

    result = make_service(repo).import_employees(content, dry_run=True)

    assert result.valid == 1
    assert result.inserted == 0
    assert repo.inserted == []


def test_any_invalid_row_blocks_the_whole_import() -> None:
    repo = FakeCsvRepository()
    content = csv_bytes(
        "Ada,Lovelace,ada@acme.test,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01",
        "Bad,Row,not-an-email,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01",
    )

    result = make_service(repo).import_employees(content, dry_run=False)

    assert result.failed == 1
    assert result.inserted == 0
    assert repo.inserted == []
    assert result.errors[0].row_number == 2
    assert result.errors[0].field == "email"


def test_duplicate_email_within_file_is_rejected() -> None:
    repo = FakeCsvRepository()
    content = csv_bytes(
        "Ada,Lovelace,dup@acme.test,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01",
        "Alan,Turing,dup@acme.test,Engineering,Engineer,L5,Full-time,US,150000.00,2020-02-02",
    )

    result = make_service(repo).import_employees(content, dry_run=False)

    assert result.failed == 1
    assert "Duplicate" in result.errors[0].message


def test_email_already_in_database_is_rejected() -> None:
    repo = FakeCsvRepository(existing_emails={"taken@acme.test"})
    content = csv_bytes(
        "Ada,Lovelace,taken@acme.test,Engineering,Engineer,L3,Full-time,US,120000.00,2021-01-01"
    )

    result = make_service(repo).import_employees(content, dry_run=False)

    assert result.failed == 1
    assert "exists" in result.errors[0].message


def test_wrong_header_is_rejected() -> None:
    repo = FakeCsvRepository()
    content = b"name,salary\nAda,100\n"

    with pytest.raises(ValidationError):
        make_service(repo).import_employees(content, dry_run=False)


def test_export_emits_header_and_one_line_per_employee() -> None:
    employee = Employee(
        employee_code="EMP-00001",
        first_name="Ada",
        last_name="Lovelace",
        email="ada@acme.test",
        department="Engineering",
        job_title="Engineer",
        level="L3",
        employment_type="Full-time",
        country="US",
        currency="USD",
        base_salary_minor=120_000_00,
        base_salary_usd_minor=120_000_00,
        hire_date=date(2021, 1, 1),
    )
    repo = FakeCsvRepository(employees=[employee])

    output = "".join(make_service(repo).export_csv(EmployeeFilters()))

    lines = output.strip().splitlines()
    assert lines[0].startswith("employee_code,")
    assert "EMP-00001" in lines[1]
    assert "ada@acme.test" in lines[1]
