"""Natural-language Q&A: question in, safe answer out.

Orchestrates the guarded path: check the session cache, otherwise prompt the model,
**validate the generated SQL through the guard**, execute it read-only with a hard row
cap, and return the rows. Raw model output and internal errors are never surfaced to the
user — failures log internally (with the request id) and return a generic message.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import QaUnavailableError
from app.core.logging import get_logger
from app.llm.client import LlmClient
from app.llm.prompt import build_system_prompt
from app.llm.sql_guard import validate_sql
from app.schemas.qa import QueryAnswer

logger = get_logger(__name__)

MAX_RESULT_ROWS = 1000
_GENERIC_FAILURE = "I couldn't answer that one. Try rephrasing the question."


class QaService:
    """Turns a question into a guarded, capped, read-only SQL result."""

    def __init__(self, client: LlmClient, session: Session, cache: dict[str, str]) -> None:
        self._client = client
        self._session = session
        self._cache = cache

    def respond_to_natural_language_query(self, question: str) -> QueryAnswer:
        """Answer a natural-language question with guarded, read-only SQL.

        Args:
            question: The HR manager's plain-English question.

        Returns:
            A :class:`QueryAnswer` with the executed SQL and result rows.

        Raises:
            QaUnavailableError: If the model fails, the SQL is rejected by the guard,
                or execution errors. The message is always generic; details are logged.
        """
        sql = self._sql_for(question)
        return self._execute(question, sql)

    def _sql_for(self, question: str) -> str:
        """Return validated SQL for the question, from cache or a fresh generation."""
        cache_key = hashlib.sha256(question.encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            candidate = self._client.generate_sql(build_system_prompt(), question)
        except Exception as exc:
            # Deliberately broad: any model/client failure must surface as the generic
            # message, never the raw error (CLAUDE.md §7). The reason is logged, not returned.
            logger.warning("qa_llm_error", error=str(exc))
            raise QaUnavailableError(_GENERIC_FAILURE) from exc

        verdict = validate_sql(candidate)
        if not verdict.allowed or verdict.sql is None:
            logger.warning("qa_sql_rejected", reason=verdict.reason)
            raise QaUnavailableError(_GENERIC_FAILURE)

        self._cache[cache_key] = verdict.sql
        return verdict.sql

    def _execute(self, question: str, sql: str) -> QueryAnswer:
        """Execute guarded SQL with a row cap and shape the result."""
        try:
            result = self._session.execute(text(sql))
            columns = list(result.keys())
            fetched = result.fetchmany(MAX_RESULT_ROWS + 1)
        except SQLAlchemyError as exc:
            logger.warning("qa_execution_error", error=str(exc))
            raise QaUnavailableError(_GENERIC_FAILURE) from exc

        truncated = len(fetched) > MAX_RESULT_ROWS
        rows = [
            {column: _jsonify(value) for column, value in zip(columns, row, strict=True)}
            for row in fetched[:MAX_RESULT_ROWS]
        ]
        return QueryAnswer(
            question=question,
            sql=sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
        )


def _jsonify(value: object) -> object:
    """Coerce a DB value to a JSON-serializable primitive."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)
