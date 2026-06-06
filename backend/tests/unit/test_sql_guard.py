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
    # Boolean/comparison operators in WHERE/HAVING must pass: sqlglot models AND/OR as
    # Func subclasses, which previously tripped the function allowlist (regression).
    "SELECT department, avg(base_salary_usd_minor) FROM employees "
    "WHERE deleted_at IS NULL AND country = 'IN' GROUP BY department",
    "SELECT count(*) FROM employees WHERE country = 'US' OR country = 'GB'",
    "SELECT department, count(*) FROM employees WHERE deleted_at IS NULL "
    "GROUP BY department HAVING count(*) > 5 AND avg(base_salary_usd_minor) < 100000000",
    # CTEs + window functions are allowed (ranking / "top 10%" questions).
    "WITH ranked AS (SELECT department, NTILE(10) OVER (ORDER BY base_salary_usd_minor DESC) "
    "AS pct FROM employees WHERE deleted_at IS NULL) "
    "SELECT department, count(*) FROM ranked WHERE pct = 1 GROUP BY department",
    "SELECT department, base_salary_usd_minor, "
    "ROW_NUMBER() OVER (PARTITION BY department ORDER BY base_salary_usd_minor DESC) AS rn "
    "FROM employees WHERE deleted_at IS NULL",
    # CAST + nested subquery (the "top 10% overrepresentation" shape).
    "SELECT department, CAST(SUM(CASE WHEN pct = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) AS ratio "
    "FROM (SELECT department, NTILE(10) OVER (ORDER BY base_salary_usd_minor DESC) AS pct "
    "FROM employees WHERE deleted_at IS NULL) GROUP BY department",
    # A stray comment is stripped, not rejected — the query is still a valid single SELECT.
    "SELECT department FROM employees -- inline note\nWHERE deleted_at IS NULL",
    "SELECT department FROM employees /* block note */ WHERE deleted_at IS NULL",
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
    "SELECT randomblob(1000000000) FROM employees",
    "SELECT zeroblob(1000000000) FROM employees",
    # A comment may not smuggle a second statement (the ';' is still caught).
    "SELECT department FROM employees -- harmless\n; DROP TABLE employees",
    "PRAGMA table_info(employees)",
    "ATTACH DATABASE 'x.db' AS x",
    "",
    "SELECT base_salary_minor FROM employees WHERE id = (SELECT id FROM users)",
    # A CTE must not become a back door to a disallowed table or system catalog.
    "WITH leak AS (SELECT * FROM users) SELECT * FROM leak",
    "WITH leak AS (SELECT * FROM sqlite_master) SELECT * FROM leak",
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


def test_comments_are_stripped_from_executed_sql() -> None:
    result = validate_sql(
        "SELECT department FROM employees /* secret */ WHERE deleted_at IS NULL -- tail"
    )

    assert result.allowed, result.reason
    assert result.sql is not None
    assert "/*" not in result.sql
    assert "secret" not in result.sql
    assert "--" not in result.sql
