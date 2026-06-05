"""Integration test for the seed script against an in-memory database."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.fx_rate import FxRate
from app.seed.reference_data import DEFAULT_FX_RATES_MICROS
from app.seed.seed import seed_database, seed_if_empty


def test_seed_inserts_employees_and_fx_rates(db_session: Session) -> None:
    inserted = seed_database(db_session, employee_count=200, faker_seed=7)

    assert inserted == 200
    assert db_session.scalar(select(func.count()).select_from(Employee)) == 200
    assert db_session.scalar(select(func.count()).select_from(FxRate)) == len(
        DEFAULT_FX_RATES_MICROS
    )


def test_seeded_employees_have_codes_and_normalized_salaries(db_session: Session) -> None:
    seed_database(db_session, employee_count=200, faker_seed=7)
    employees = list(db_session.scalars(select(Employee)).all())

    assert len({employee.employee_code for employee in employees}) == 200  # codes are unique
    assert all(employee.base_salary_usd_minor > 0 for employee in employees)
    assert all(employee.base_salary_minor > 0 for employee in employees)


def test_seed_is_idempotent_replacing_prior_data(db_session: Session) -> None:
    seed_database(db_session, employee_count=50, faker_seed=1)
    seed_database(db_session, employee_count=30, faker_seed=1)

    assert db_session.scalar(select(func.count()).select_from(Employee)) == 30


def test_seed_if_empty_seeds_a_fresh_database(db_session: Session) -> None:
    inserted = seed_if_empty(db_session, employee_count=40, faker_seed=3)

    assert inserted == 40
    assert db_session.scalar(select(func.count()).select_from(Employee)) == 40


def test_seed_if_empty_is_a_noop_when_already_populated(db_session: Session) -> None:
    seed_database(db_session, employee_count=40, faker_seed=3)

    inserted = seed_if_empty(db_session, employee_count=10, faker_seed=3)

    assert inserted == 0
    assert db_session.scalar(select(func.count()).select_from(Employee)) == 40
