"""CSV import and export — the on-ramp off spreadsheets and back out again.

Import is **all-or-nothing**: every row is validated first; if any row fails, nothing
is written and all errors are returned with row numbers. A ``dry_run`` validates without
writing (the UI's "preview before import"). Valid rows are inserted in bulk in a single
transaction. Export streams the current, filtered view back as CSV.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Iterator
from typing import Protocol

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.domain.country import Country
from app.domain.currency import Currency
from app.domain.currency_converter import CurrencyConverter
from app.domain.money import Money
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeFilters
from app.schemas.employee import EmployeeCreate
from app.schemas.imports import ImportResult, ImportRowError

MAX_CSV_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# The exact columns an import CSV must contain (order-independent on read, fixed on export).
CSV_COLUMNS = (
    "first_name",
    "last_name",
    "email",
    "department",
    "job_title",
    "level",
    "employment_type",
    "country",
    "base_salary_amount",
    "hire_date",
)
_EXPORT_COLUMNS = (
    "employee_code",
    *CSV_COLUMNS[:-1],  # everything except base_salary_amount keeps its place
    "currency",
    "base_salary_amount",
    "base_salary_usd",
    "hire_date",
)


class CsvEmployeeRepository(Protocol):
    """The employee data access the CSV service needs."""

    def get_by_email(self, email: str) -> Employee | None: ...

    def max_id(self) -> int: ...

    def bulk_insert(self, rows: list[dict[str, object]]) -> None: ...

    def iter_filtered(self, filters: EmployeeFilters) -> Iterator[Employee]: ...


class EmployeeCsvService:
    """Validate-and-bulk-import employees from CSV, and export them back out."""

    def __init__(
        self,
        repository: CsvEmployeeRepository,
        converter: CurrencyConverter,
        session: Session,
    ) -> None:
        self._repository = repository
        self._converter = converter
        self._session = session

    def import_employees(self, content: bytes, *, dry_run: bool) -> ImportResult:
        """Validate every row, then bulk-insert all of them or none.

        Args:
            content: Raw CSV bytes (UTF-8, BOM tolerant).
            dry_run: If True, validate and report but never write.

        Returns:
            An :class:`ImportResult` with per-row errors and counts.

        Raises:
            ValidationError: If the file is too large or its header is wrong.
        """
        if len(content) > MAX_CSV_SIZE_BYTES:
            raise ValidationError("CSV file exceeds the 10 MB limit.")

        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        self._require_expected_header(reader.fieldnames)

        valid: list[EmployeeCreate] = []
        errors: list[ImportRowError] = []
        seen_emails: set[str] = set()
        total = 0

        for row_number, raw in enumerate(reader, start=1):
            total += 1
            error = self._validate_row(row_number, raw, seen_emails)
            if isinstance(error, EmployeeCreate):
                valid.append(error)
                seen_emails.add(error.email)
            else:
                errors.append(error)

        should_insert = not dry_run and not errors
        if should_insert:
            self._repository.bulk_insert(self._build_rows(valid))
            self._session.commit()

        return ImportResult(
            total=total,
            valid=len(valid),
            failed=len(errors),
            inserted=len(valid) if should_insert else 0,
            dry_run=dry_run,
            errors=errors,
        )

    def export_csv(self, filters: EmployeeFilters) -> Iterator[str]:
        """Yield the filtered employees as CSV text, header first, then one line per row."""
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        def take() -> str:
            value = buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
            return value

        writer.writerow(_EXPORT_COLUMNS)
        yield take()

        for employee in self._repository.iter_filtered(filters):
            writer.writerow(self._export_row(employee))
            yield take()

    def _validate_row(
        self, row_number: int, raw: dict[str, str | None], seen_emails: set[str]
    ) -> EmployeeCreate | ImportRowError:
        """Validate one CSV row into an EmployeeCreate or an error."""
        try:
            candidate = EmployeeCreate.model_validate({key: raw.get(key) for key in CSV_COLUMNS})
        except PydanticValidationError as exc:
            first = exc.errors()[0]
            field = str(first["loc"][-1]) if first["loc"] else None
            return ImportRowError(row_number=row_number, field=field, message=first["msg"])

        if candidate.email in seen_emails:
            return ImportRowError(
                row_number=row_number, field="email", message="Duplicate email within the file."
            )
        if self._repository.get_by_email(candidate.email) is not None:
            return ImportRowError(
                row_number=row_number, field="email", message="Email already exists."
            )
        return candidate

    def _build_rows(self, employees: list[EmployeeCreate]) -> list[dict[str, object]]:
        """Turn validated rows into insert mappings with derived code/currency/USD."""
        base_id = self._repository.max_id()
        rows: list[dict[str, object]] = []
        for offset, data in enumerate(employees, start=1):
            currency = Country(data.country).default_currency
            local_salary = Money(data.base_salary_amount, currency)
            rows.append(
                {
                    "employee_code": f"EMP-{base_id + offset:05d}",
                    "first_name": data.first_name,
                    "last_name": data.last_name,
                    "email": data.email,
                    "department": data.department.value,
                    "job_title": data.job_title,
                    "level": data.level.value,
                    "employment_type": data.employment_type.value,
                    "country": data.country,
                    "currency": currency.code,
                    "base_salary_minor": local_salary.to_minor_units(),
                    "base_salary_usd_minor": self._converter.to_base(local_salary).to_minor_units(),
                    "hire_date": data.hire_date,
                }
            )
        return rows

    def _export_row(self, employee: Employee) -> list[object]:
        currency = Currency(employee.currency)
        local_salary = Money.from_minor_units(employee.base_salary_minor, currency)
        usd_salary = Money.from_minor_units(
            employee.base_salary_usd_minor, self._converter.base_currency
        )
        return [
            employee.employee_code,
            employee.first_name,
            employee.last_name,
            employee.email,
            employee.department,
            employee.job_title,
            employee.level,
            employee.employment_type,
            employee.country,
            currency.code,
            local_salary.amount,
            usd_salary.amount,
            employee.hire_date.isoformat(),
        ]

    @staticmethod
    def _require_expected_header(fieldnames: Iterable[str] | None) -> None:
        actual = set(fieldnames or [])
        expected = set(CSV_COLUMNS)
        if actual != expected:
            missing = expected - actual
            unexpected = actual - expected
            raise ValidationError(
                "CSV header does not match the expected columns.",
                details={"missing": sorted(missing), "unexpected": sorted(unexpected)},
            )
