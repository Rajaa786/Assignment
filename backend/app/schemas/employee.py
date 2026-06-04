"""Transport schemas for employees: create, partial-update, and response shapes.

These define the API contract. Salary arrives and leaves in **major units** (what a
human types, e.g. ``95000.00``) in the employee's local currency; the service converts
to and from the integer minor units used for storage. Currency is derived from the
country, so the two can never disagree.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.domain.country import Country, InvalidCountryError
from app.domain.enums import Department, EmploymentType, Level
from app.schemas.common import MoneyOut

# Pragmatic email check that avoids pulling in the email-validator dependency for an
# internal tool: a non-empty local part, an @, and a dotted domain.
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
EmailStr = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=254, pattern=_EMAIL_PATTERN)
]
JobTitleStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
PositiveAmount = Annotated[
    Decimal, Field(gt=0, description="Salary in major units, local currency.")
]


def _validate_country(code: str) -> str:
    """Validate and normalize an ISO 3166 country code, raising on unsupported."""
    try:
        return Country(code.upper()).code
    except InvalidCountryError as exc:
        raise ValueError(str(exc)) from exc


class EmployeeCreate(BaseModel):
    """Payload to create an employee. Currency and code are derived server-side."""

    first_name: NameStr
    last_name: NameStr
    email: EmailStr
    department: Department
    job_title: JobTitleStr
    level: Level
    employment_type: EmploymentType
    country: str = Field(description="ISO 3166-1 alpha-2 country code.")
    base_salary_amount: PositiveAmount
    hire_date: date

    @field_validator("country")
    @classmethod
    def _country_supported(cls, value: str) -> str:
        return _validate_country(value)


class EmployeeUpdate(BaseModel):
    """Partial update (PATCH). Any provided field replaces the current value."""

    first_name: NameStr | None = None
    last_name: NameStr | None = None
    email: EmailStr | None = None
    department: Department | None = None
    job_title: JobTitleStr | None = None
    level: Level | None = None
    employment_type: EmploymentType | None = None
    country: str | None = None
    base_salary_amount: PositiveAmount | None = None
    hire_date: date | None = None

    @field_validator("country")
    @classmethod
    def _country_supported(cls, value: str | None) -> str | None:
        return None if value is None else _validate_country(value)


class EmployeeResponse(BaseModel):
    """An employee as returned by the API.

    Salary is given twice: ``base_salary`` in the employee's local currency and
    ``base_salary_usd`` normalized to USD for cross-country comparison.
    """

    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    department: str
    job_title: str
    level: str
    employment_type: str
    country: str
    country_name: str
    base_salary: MoneyOut
    base_salary_usd: MoneyOut
    hire_date: date
    created_at: datetime
    updated_at: datetime
