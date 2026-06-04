"""Adversarial unit tests for the LLM SQL guard.

These are the security-critical tests: every known class of attack must be rejected,
and legitimate analytical queries must pass.
"""

from __future__ import annotations

import pytest

from app.llm.sql_guard import validate_sql

ALLOWED_QUERIES = [
    "SELECT department, count(*) FROM employees WHERE deleted_at IS NULL GROUP BY department",
    "SELECT round(avg(base_salary_usd_minor) / 100.0, 2) FROM employees",
    "SELECT * FROM fx_rates",
    "SELECT country, sum(base_salary_usd_minor) FROM employees GROUP BY country",
]

REJECTED_QUERIES = [
    "DROP TABLE employees",
    "DELETE FROM employees",
    "UPDATE employees SET base_salary_minor = 0",
    "INSERT INTO employees (id) VALUES (1)",
    "SELECT * FROM employees; DROP TABLE employees",
    "SELECT * FROM sqlite_master",
    "SELECT * FROM pg_catalog.pg_tables",
    "SELECT * FROM users",
    "SELECT load_extension('evil.so') FROM employees",
    "SELECT department FROM employees -- sneaky comment",
    "SELECT department FROM employees /* block comment */",
    "PRAGMA table_info(employees)",
    "ATTACH DATABASE 'x.db' AS x",
    "",
    "SELECT base_salary_minor FROM employees WHERE id = (SELECT id FROM users)",
]


@pytest.mark.parametrize("sql", ALLOWED_QUERIES)
def test_legitimate_select_is_allowed(sql: str) -> None:
    result = validate_sql(sql)

    assert result.allowed, result.reason
    assert result.sql is not None


@pytest.mark.parametrize("sql", REJECTED_QUERIES)
def test_dangerous_or_invalid_sql_is_rejected(sql: str) -> None:
    result = validate_sql(sql)

    assert not result.allowed
    assert result.sql is None


def test_overlong_statement_is_rejected() -> None:
    long_sql = "SELECT " + ", ".join(["department"] * 500) + " FROM employees"

    assert not validate_sql(long_sql).allowed
