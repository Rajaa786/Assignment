"""System-prompt construction for the natural-language Q&A feature.

The prompt gives the model exactly what it needs to write a correct, safe query and
nothing more: the schema (tables, columns, types), the small categorical vocabularies
(departments, levels, countries) so it uses real values, and hard rules — SELECT only,
one statement, no comments, no semicolons. Salaries are integer minor units, so the
prompt tells the model to divide by 100 when reporting dollar amounts.
"""

from __future__ import annotations

from app.domain.country import supported_country_codes
from app.domain.enums import Department, EmploymentType, Level

_SCHEMA = """\
Table employees:
  id INTEGER, employee_code TEXT, first_name TEXT, last_name TEXT, email TEXT,
  department TEXT, job_title TEXT, level TEXT, employment_type TEXT,
  country TEXT (ISO 3166 alpha-2), currency TEXT (ISO 4217),
  base_salary_minor INTEGER (salary in local currency, MINOR units e.g. cents),
  base_salary_usd_minor INTEGER (salary normalized to USD, MINOR units),
  hire_date DATE, deleted_at DATETIME (NULL means active)

Table fx_rates:
  currency TEXT, rate_to_usd_micros INTEGER, updated_at DATETIME"""


def build_system_prompt() -> str:
    """Return the system prompt instructing the model to emit one safe SELECT.

    Returns:
        A prompt embedding the schema, the categorical value vocabularies, and the
        non-negotiable safety rules. Deterministic, so it is cache-friendly.
    """
    departments = ", ".join(member.value for member in Department)
    levels = ", ".join(member.value for member in Level)
    employment_types = ", ".join(member.value for member in EmploymentType)
    countries = ", ".join(supported_country_codes())

    return f"""\
You translate an HR manager's question into ONE read-only SQLite SELECT query over the
schema below. Output ONLY the SQL — no prose, no markdown, no comments, no semicolon.

{_SCHEMA}

Valid values:
  department: {departments}
  level: {levels}
  employment_type: {employment_types}
  country: {countries}

Rules:
- A single SELECT statement only. Never INSERT/UPDATE/DELETE/DDL/PRAGMA.
- You may use standard read-only SQLite functions: aggregates (avg, min, max, sum, count,
  total, group_concat), math (round, abs, sign, ceil, floor, mod), null/type handling
  (coalesce, nullif, ifnull, cast, iif), string (lower, upper, length, substr, trim,
  replace, instr), date/time (date, datetime, strftime, julianday), and window functions
  (row_number, rank, dense_rank, ntile, percent_rank, cume_dist, lag, lead, first_value,
  last_value) with OVER (...). Do NOT use load_extension or any file/system function.
- CTEs (WITH ... AS (...)) and subqueries are allowed. For "top N%" / ranking / percentile
  questions, prefer NTILE or PERCENT_RANK.
- Always filter out soft-deleted rows with: deleted_at IS NULL.
- Salaries are MINOR units; for dollar amounts compute base_salary_usd_minor / 100.0.
- For cross-country comparison use base_salary_usd_minor, not base_salary_minor.
- Never reference any table other than employees or fx_rates."""
