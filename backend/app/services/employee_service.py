"""Business logic for employees: the orchestration layer between API and data.

This is where the rules live: currency is derived from country, the USD-normalized
salary is computed on every write, employee codes are generated, and ORM rows are
mapped explicitly to response schemas (no ``from_orm`` magic). The service owns the
transaction boundary — routers never commit, repositories never commit.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, EmployeeNotFoundError
from app.core.pagination import SortDirection
from app.domain.country import Country
from app.domain.currency import Currency
from app.domain.currency_converter import CurrencyConverter
from app.domain.money import Money
from app.models.employee import Employee
from app.repositories.employee_repository import (
    EmployeeFilters,
    EmployeeReader,
    EmployeeWriter,
)
from app.schemas.common import MoneyOut, Page
from app.schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate


class EmployeeService:
    """Create, read, update, soft-delete, and list employees.

    Depends on narrow repository protocols (read and write) and a currency
    converter, all injected — never imported — so the service is unit-testable
    with fakes and the data/FX sources are swappable.
    """

    def __init__(
        self,
        reader: EmployeeReader,
        writer: EmployeeWriter,
        converter: CurrencyConverter,
        session: Session,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._converter = converter
        self._session = session

    def create_employee(self, data: EmployeeCreate) -> EmployeeResponse:
        """Create an employee, deriving currency, USD salary, and employee code.

        Raises:
            ConflictError: If the email is already in use.
        """
        self._ensure_email_available(data.email)

        country = Country(data.country)
        currency = country.default_currency
        local_salary = Money(data.base_salary_amount, currency)

        employee = Employee(
            employee_code="",  # filled after flush, when the id is known
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            department=data.department.value,
            job_title=data.job_title,
            level=data.level.value,
            employment_type=data.employment_type.value,
            country=country.code,
            currency=currency.code,
            base_salary_minor=local_salary.to_minor_units(),
            base_salary_usd_minor=self._converter.to_base(local_salary).to_minor_units(),
            hire_date=data.hire_date,
        )
        self._writer.add(employee)
        self._session.flush()
        employee.employee_code = f"EMP-{employee.id:05d}"
        self._commit()
        self._session.refresh(employee)
        return self._to_response(employee)

    def get_employee(self, employee_id: int) -> EmployeeResponse:
        """Return one employee.

        Raises:
            EmployeeNotFoundError: If no active employee has this id.
        """
        return self._to_response(self._require_employee(employee_id))

    def update_employee(self, employee_id: int, data: EmployeeUpdate) -> EmployeeResponse:
        """Apply a partial update, recomputing salary normalization when needed.

        Salary is recomputed if the amount changes or the country (hence currency)
        changes. Raises:
            EmployeeNotFoundError: If no active employee has this id.
            ConflictError: If the new email is already used by another employee.
        """
        employee = self._require_employee(employee_id)
        changes = data.model_dump(exclude_unset=True)

        if "email" in changes and changes["email"] != employee.email:
            self._ensure_email_available(changes["email"])

        self._apply_simple_fields(employee, changes)
        self._apply_salary_and_currency(employee, data)

        self._commit()
        self._session.refresh(employee)
        return self._to_response(employee)

    def delete_employee(self, employee_id: int) -> None:
        """Soft-delete an employee (sets ``deleted_at``).

        Raises:
            EmployeeNotFoundError: If no active employee has this id.
        """
        employee = self._require_employee(employee_id)
        self._writer.soft_delete(employee)
        self._commit()

    def list_employees(
        self,
        filters: EmployeeFilters,
        *,
        sort_by: str,
        sort_dir: SortDirection,
        cursor: str | None,
        limit: int,
    ) -> Page[EmployeeResponse]:
        """Return one cursor page of employees plus the total matching count."""
        rows, next_cursor = self._reader.page(
            filters, sort_by=sort_by, sort_dir=sort_dir, cursor=cursor, limit=limit
        )
        total = self._reader.count(filters)
        return Page(
            items=[self._to_response(row) for row in rows],
            next_cursor=next_cursor,
            total=total,
        )

    def _require_employee(self, employee_id: int) -> Employee:
        employee = self._reader.get_by_id(employee_id)
        if employee is None:
            raise EmployeeNotFoundError(
                f"No employee with id {employee_id}", details={"employee_id": employee_id}
            )
        return employee

    def _ensure_email_available(self, email: str) -> None:
        if self._reader.get_by_email(email) is not None:
            raise ConflictError(f"Email already in use: {email}", details={"email": email})

    @staticmethod
    def _apply_simple_fields(employee: Employee, changes: dict[str, object]) -> None:
        """Copy non-salary, non-currency fields from a partial update onto the row."""
        for field in (
            "first_name",
            "last_name",
            "email",
            "job_title",
            "department",
            "level",
            "employment_type",
            "hire_date",
        ):
            if field in changes:
                value = changes[field]
                # StrEnum members serialize to their string value for storage.
                setattr(employee, field, value.value if hasattr(value, "value") else value)

    def _apply_salary_and_currency(self, employee: Employee, data: EmployeeUpdate) -> None:
        """Recompute currency and normalized salary when country or amount changes."""
        country_changed = data.country is not None and data.country != employee.country
        amount_changed = data.base_salary_amount is not None
        if not country_changed and not amount_changed:
            return

        currency = (
            Country(data.country).default_currency
            if data.country is not None
            else Currency(employee.currency)
        )
        current_amount = Money.from_minor_units(
            employee.base_salary_minor, Currency(employee.currency)
        ).amount
        amount = data.base_salary_amount if data.base_salary_amount is not None else current_amount
        local_salary = Money(amount, currency)

        employee.country = data.country if data.country is not None else employee.country
        employee.currency = currency.code
        employee.base_salary_minor = local_salary.to_minor_units()
        employee.base_salary_usd_minor = self._converter.to_base(local_salary).to_minor_units()

    def _commit(self) -> None:
        """Commit the current transaction, translating uniqueness races to conflicts."""
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("A conflicting record already exists.") from exc

    def _to_response(self, employee: Employee) -> EmployeeResponse:
        """Map an ORM employee to its response schema, reconstructing money exactly."""
        currency = Currency(employee.currency)
        base_currency = self._converter.base_currency
        local_salary = Money.from_minor_units(employee.base_salary_minor, currency)
        usd_salary = Money.from_minor_units(employee.base_salary_usd_minor, base_currency)
        return EmployeeResponse(
            id=employee.id,
            employee_code=employee.employee_code,
            first_name=employee.first_name,
            last_name=employee.last_name,
            email=employee.email,
            department=employee.department,
            job_title=employee.job_title,
            level=employee.level,
            employment_type=employee.employment_type,
            country=employee.country,
            country_name=Country(employee.country).display_name,
            base_salary=MoneyOut(
                amount=local_salary.amount,
                currency=currency.code,
                minor_units=employee.base_salary_minor,
            ),
            base_salary_usd=MoneyOut(
                amount=usd_salary.amount,
                currency=base_currency.code,
                minor_units=employee.base_salary_usd_minor,
            ),
            hire_date=employee.hire_date,
            created_at=employee.created_at,
            updated_at=employee.updated_at,
        )
