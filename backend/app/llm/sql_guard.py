"""The SQL guard — the safety boundary for LLM-generated queries.

Generated SQL is parsed into an AST (sqlglot) and inspected, not pattern-matched:
the statement must be a single ``SELECT``/``UNION`` over whitelisted tables, using
only an allowlist of functions, with no DDL/DML, no multiple statements, no comments,
and no system-catalog access. Anything else is rejected before a single character
reaches the database. This is a deny-by-default gate (``ADR-0004``).
"""

from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp

# Tables the Q&A feature may read. Anything else — including pg_* and sqlite_master —
# is not on this list and is therefore rejected.
ALLOWED_TABLES = frozenset({"employees", "fx_rates"})

# The only SQL functions permitted in generated queries. Aggregates/scalars plus the
# read-only window functions needed for ranking/percentile questions (e.g. "top 10%").
# All are pure read operations; the OVER clause itself carries no extra privilege.
ALLOWED_FUNCTIONS = frozenset(
    {
        "avg",
        "min",
        "max",
        "sum",
        "count",
        "round",
        "coalesce",
        "lower",
        "upper",
        # Window functions (used with OVER (...)).
        "row_number",
        "rank",
        "dense_rank",
        "ntile",
        "percent_rank",
        "cume_dist",
        "lag",
        "lead",
        "first_value",
        "last_value",
    }
)

# AST node types that must never appear (DDL/DML and out-of-band commands).
_FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Command,  # PRAGMA, VACUUM, ATTACH, and anything sqlglot can't model
    exp.Set,
    exp.Into,
)

MAX_SQL_LENGTH = 2000


@dataclass(frozen=True, slots=True)
class GuardResult:
    """The verdict from the guard.

    Attributes:
        allowed: Whether the SQL passed every check.
        reason: Why it was rejected (for internal logging), or ``None`` if allowed.
        sql: The normalized SQL to execute, or ``None`` if rejected.
    """

    allowed: bool
    reason: str | None = None
    sql: str | None = None


def _reject(reason: str) -> GuardResult:
    return GuardResult(allowed=False, reason=reason)


def validate_sql(sql: str) -> GuardResult:
    """Validate LLM-generated SQL against the safety policy.

    Args:
        sql: The candidate SQL string from the model.

    Returns:
        A :class:`GuardResult`; ``allowed`` is True only if every check passes.
    """
    stripped = sql.strip()
    if not stripped:
        return _reject("empty statement")
    if len(stripped) > MAX_SQL_LENGTH:
        return _reject("statement exceeds length limit")
    if "--" in stripped or "/*" in stripped or "*/" in stripped:
        return _reject("comments are not allowed")
    if ";" in stripped.rstrip(";"):
        return _reject("multiple statements are not allowed")

    try:
        parsed = sqlglot.parse(stripped, read="sqlite")
    except sqlglot.errors.ParseError:
        return _reject("could not parse SQL")
    statements = [statement for statement in parsed if statement]

    if len(statements) != 1:
        return _reject("exactly one statement is required")

    statement = statements[0]
    if not isinstance(statement, exp.Select | exp.Union):
        return _reject(f"only SELECT is allowed, got {type(statement).__name__}")

    for node in statement.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            return _reject(f"forbidden operation: {type(node).__name__}")

    # CTE names (WITH x AS (...)) are local aliases, not base tables — allow references
    # to them. Their bodies are still walked, so a CTE selecting from a disallowed real
    # table (e.g. WITH t AS (SELECT * FROM users)) is still rejected below.
    cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
    allowed_tables = ALLOWED_TABLES | cte_names
    for table in statement.find_all(exp.Table):
        if table.name.lower() not in allowed_tables:
            return _reject(f"table not allowed: {table.name}")

    for function in statement.find_all(exp.Func):
        # sqlglot models boolean/comparison/arithmetic operators (AND, OR, =, +, …) as
        # Func subclasses via Connector/Binary/Unary. Those are operators, not callable
        # functions, so they bypass the allowlist — a genuine function call is never a
        # Connector/Binary/Unary (e.g. load_extension parses as exp.Anonymous). Without
        # this, any query with a WHERE ... AND ... is wrongly rejected.
        if isinstance(function, exp.Connector | exp.Binary | exp.Unary):
            continue
        name = _function_name(function)
        if name not in ALLOWED_FUNCTIONS:
            return _reject(f"function not allowed: {name}")

    return GuardResult(allowed=True, sql=statement.sql(dialect="sqlite"))


def _function_name(function: exp.Func) -> str:
    """Return the lowercase name of a function node, for known and anonymous funcs."""
    if isinstance(function, exp.Anonymous):
        return str(function.name).lower()
    return function.sql_name().lower()
