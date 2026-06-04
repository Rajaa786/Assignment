"""Seed the database with 10,000 realistic, multi-country employees.

Run after migrations: ``python -m app.seed.seed``. Generation is deterministic (fixed
Faker/RNG seed) so every run produces the same data, and insertion is a single bulk
statement in one transaction — 10k rows in well under the 10-second budget
(``CLAUDE.md`` §9). Salaries are sized per country and level so the data looks plausible
and the USD-normalized comparisons are meaningful.
"""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from faker import Faker
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging, get_logger
from app.domain.country import Country, supported_country_codes
from app.domain.currency import Currency
from app.domain.enums import Department, EmploymentType, Level
from app.domain.money import Money
from app.models.employee import Employee
from app.models.fx_rate import FxRate
from app.seed.reference_data import (
    DEFAULT_FX_RATES_MICROS,
    L1_BASE_SALARY_BY_CURRENCY,
    LEVEL_MULTIPLIERS,
)
from app.services.currency_converter import FxTableCurrencyConverter

logger = get_logger(__name__)

DEFAULT_EMPLOYEE_COUNT = 10_000
FAKER_SEED = 42

_COUNTRIES = supported_country_codes()
_DEPARTMENTS = [member.value for member in Department]
_LEVELS = [member.value for member in Level]
_EMPLOYMENT_TYPES = [member.value for member in EmploymentType]
# Most employees are full-time; weight accordingly for realism.
_EMPLOYMENT_WEIGHTS = [0.85, 0.08, 0.07]


def seed_database(
    session: Session,
    *,
    employee_count: int = DEFAULT_EMPLOYEE_COUNT,
    faker_seed: int = FAKER_SEED,
) -> int:
    """Replace all data with a freshly generated set of employees and FX rates.

    Args:
        session: An open session; this function owns the transaction (commits once).
        employee_count: How many employees to generate.
        faker_seed: Seed for deterministic names and randomness.

    Returns:
        The number of employees inserted.
    """
    faker = Faker()
    Faker.seed(faker_seed)
    rng = random.Random(faker_seed)

    session.execute(delete(Employee))
    session.execute(delete(FxRate))
    session.add_all(
        FxRate(currency=code, rate_to_usd_micros=micros)
        for code, micros in DEFAULT_FX_RATES_MICROS.items()
    )
    session.flush()

    converter = FxTableCurrencyConverter(DEFAULT_FX_RATES_MICROS, Currency(settings.base_currency))
    rows = [
        _make_employee_row(index, faker, rng, converter)
        for index in range(1, employee_count + 1)
    ]
    session.execute(insert(Employee), rows)
    session.commit()
    return len(rows)


def _make_employee_row(
    index: int,
    faker: Faker,
    rng: random.Random,
    converter: FxTableCurrencyConverter,
) -> dict[str, object]:
    """Build one employee insert-mapping with a country-appropriate salary."""
    country = Country(rng.choice(_COUNTRIES))
    currency = country.default_currency
    level = rng.choice(_LEVELS)

    base = L1_BASE_SALARY_BY_CURRENCY[currency.code] * LEVEL_MULTIPLIERS[level]
    jittered = base * rng.uniform(0.9, 1.1)
    local_salary = Money(Decimal(str(round(jittered, 2))), currency)

    first_name = faker.first_name()
    last_name = faker.last_name()
    return {
        "employee_code": f"EMP-{index:05d}",
        "first_name": first_name,
        "last_name": last_name,
        "email": f"{first_name}.{last_name}.{index}@acme.test".lower().replace(" ", ""),
        "department": rng.choice(_DEPARTMENTS),
        "job_title": f"{level} {rng.choice(_DEPARTMENTS)} Specialist",
        "level": level,
        "employment_type": rng.choices(_EMPLOYMENT_TYPES, weights=_EMPLOYMENT_WEIGHTS)[0],
        "country": country.code,
        "currency": currency.code,
        "base_salary_minor": local_salary.to_minor_units(),
        "base_salary_usd_minor": converter.to_base(local_salary).to_minor_units(),
        "hire_date": faker.date_between(start_date=date(2015, 1, 1), end_date=date(2025, 12, 31)),
    }


def main() -> None:
    """Entry point for ``python -m app.seed.seed``."""
    configure_logging()
    session = SessionLocal()
    try:
        count = seed_database(session)
        logger.info("seed_complete", employees=count)
    finally:
        session.close()


if __name__ == "__main__":
    main()
