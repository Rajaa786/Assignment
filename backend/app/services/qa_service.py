"""Natural-language Q&A: question in, safe answer out.

Orchestrates the guarded path: check the session cache, otherwise prompt the model,
**validate the generated SQL through the guard**, execute it read-only with a hard row
cap, and return the rows. Raw model output and internal errors are never surfaced to the
user — failures log internally (with the request id) and return a generic message.

Logging note: each step of the path logs at INFO the model *input* (prompt + question),
the model *output*, and the *executed* SQL, so one ``/ask`` call is fully traceable in
``docker logs`` without flipping to DEBUG. This is a deliberate, documented exception to
``CLAUDE.md`` §8 — a generated ``WHERE`` may embed a salary threshold the manager named.
Row values (actual compensation) are still never logged. See ``ADR-0013``.
"""

from __future__ import annotations

import hashlib
import time
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
# Cap how much of the manager's free-text question we log at INFO. The question is the
# user's own input (not a stored salary), but a cap keeps log lines bounded.
MAX_LOGGED_QUESTION_CHARS = 200
_GENERIC_FAILURE = "I couldn't answer that one. Try rephrasing the question."


class QaService:
    """Turns a question into a guarded, capped, read-only SQL result."""

    def __init__(self, client: LlmClient, session: Session, cache: dict[str, str]) -> None:
        self._client = client
        self._session = session
        self._cache = cache

    def respond_to_natural_language_query(self, question: str) -> QueryAnswer:
        """Answer a natural-language question with guarded, read-only SQL.

        Emits a request-scoped structured trace (``qa_request_received`` …
        ``qa_answered``); every line carries the request id bound by the middleware, so
        one ``/ask`` call is followed end to end in the logs. The prompt, model output,
        and executed SQL are logged at INFO (``ADR-0013``; documented §8 exception);
        result rows are never logged.

        Args:
            question: The HR manager's plain-English question.

        Returns:
            A :class:`QueryAnswer` with the executed SQL and result rows.

        Raises:
            QaUnavailableError: If the model fails, the SQL is rejected by the guard,
                or execution errors. The message is always generic; details are logged.
        """
        started = time.perf_counter()
        provider = self._client.describe()
        question_sha8 = _sha8(question)
        logger.info(
            "qa_request_received",
            question=question[:MAX_LOGGED_QUESTION_CHARS],
            question_sha8=question_sha8,
            provider=provider,
        )

        system_prompt = build_system_prompt()
        # INFO: the full input handed to the model — prompt + question (ADR-0013, §8
        # exception). The prompt is schema/vocab/rules; it carries no compensation values.
        logger.info("qa_prompt_built", system_prompt=system_prompt, question=question)

        sql = self._sql_for(question, system_prompt, provider, question_sha8)
        answer = self._execute(question, sql)

        logger.info(
            "qa_answered",
            provider=provider,
            row_count=answer.row_count,
            truncated=answer.truncated,
            total_latency_ms=_elapsed_ms(started),
        )
        return answer

    def _sql_for(self, question: str, system_prompt: str, provider: str, question_sha8: str) -> str:
        """Return validated SQL for the question, from cache or a fresh generation."""
        cache_key = hashlib.sha256(question.encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("qa_cache_hit", question_sha8=question_sha8, sql=cached)
            return cached

        started = time.perf_counter()
        try:
            candidate = self._client.generate_sql(system_prompt, question)
        except Exception as exc:
            # Deliberately broad: any model/client failure must surface as the generic
            # message, never the raw error (CLAUDE.md §7). The stack trace is logged
            # internally (with the request id), never returned.
            logger.warning(
                "qa_llm_error",
                provider=provider,
                error_type=type(exc).__name__,
                exc_info=exc,
            )
            raise QaUnavailableError(_GENERIC_FAILURE) from exc

        llm_latency_ms = _elapsed_ms(started)
        # INFO: the raw, pre-guard model output (ADR-0013, §8 exception). Visible so the
        # exact text the model returned can be inspected before the guard rewrites it.
        logger.info("qa_sql_candidate", provider=provider, sql=candidate)

        verdict = validate_sql(candidate)
        if not verdict.allowed or verdict.sql is None:
            logger.warning("qa_sql_rejected", reason=verdict.reason, sql_sha8=_sha8(candidate))
            raise QaUnavailableError(_GENERIC_FAILURE)

        logger.info(
            "qa_sql_generated",
            provider=provider,
            llm_latency_ms=llm_latency_ms,
            sql=verdict.sql,
            sql_chars=len(verdict.sql),
            sql_sha8=_sha8(verdict.sql),
        )
        self._cache[cache_key] = verdict.sql
        return verdict.sql

    def _execute(self, question: str, sql: str) -> QueryAnswer:
        """Execute guarded SQL with a row cap and shape the result."""
        started = time.perf_counter()
        try:
            result = self._session.execute(text(sql))
            columns = list(result.keys())
            fetched = result.fetchmany(MAX_RESULT_ROWS + 1)
        except SQLAlchemyError as exc:
            logger.warning(
                "qa_execution_error",
                error_type=type(exc).__name__,
                sql_sha8=_sha8(sql),
                exc_info=exc,
            )
            raise QaUnavailableError(_GENERIC_FAILURE) from exc

        truncated = len(fetched) > MAX_RESULT_ROWS
        rows = [
            {column: _jsonify(value) for column, value in zip(columns, row, strict=True)}
            for row in fetched[:MAX_RESULT_ROWS]
        ]
        answer = QueryAnswer(
            question=question,
            sql=sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
        )
        logger.info(
            "qa_executed",
            sql=sql,
            row_count=answer.row_count,
            truncated=truncated,
            db_latency_ms=_elapsed_ms(started),
        )
        return answer


def _sha8(value: str) -> str:
    """Return the first 8 hex chars of the SHA-256 of ``value`` — a safe log token."""
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def _elapsed_ms(started: float) -> float:
    """Return milliseconds elapsed since a ``time.perf_counter()`` start, to 1 dp."""
    return round((time.perf_counter() - started) * 1000, 1)


def _jsonify(value: object) -> object:
    """Coerce a DB value to a JSON-serializable primitive."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)
