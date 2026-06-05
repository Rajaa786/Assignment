"""FastAPI dependency providers — the composition root for the API.

Wires the request-scoped session into repositories, the currency converter, and the
services. Because every provider depends on ``get_session`` (which FastAPI caches per
request), the repository, converter, and service all share one session and therefore
one transaction. This is the only place concrete implementations are chosen; everything
downstream depends on protocols.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_session
from app.domain.currency import Currency
from app.domain.currency_converter import CurrencyConverter
from app.llm.client import LlmClient
from app.llm.factory import build_llm_client
from app.repositories.analytics_repository import SqlAnalyticsRepository
from app.repositories.employee_repository import SqlEmployeeRepository
from app.repositories.fx_repository import SqlFxRateRepository
from app.services.analytics_service import AnalyticsService
from app.services.csv_service import EmployeeCsvService
from app.services.currency_converter import FxTableCurrencyConverter
from app.services.employee_service import EmployeeService
from app.services.qa_service import QaService

# Process-wide cache of (question hash -> validated SQL) so a repeated question
# does not re-prompt the model within the running session (CLAUDE.md §7).
_QA_SQL_CACHE: dict[str, str] = {}


def get_employee_repository(session: Session = Depends(get_session)) -> SqlEmployeeRepository:
    """Provide a SQL-backed employee repository bound to the request session."""
    return SqlEmployeeRepository(session)


def get_currency_converter(session: Session = Depends(get_session)) -> CurrencyConverter:
    """Provide a currency converter seeded from the fx_rates table."""
    rates = SqlFxRateRepository(session).rates_to_usd_micros()
    return FxTableCurrencyConverter(rates, Currency(settings.base_currency))


def get_employee_service(
    repository: SqlEmployeeRepository = Depends(get_employee_repository),
    converter: CurrencyConverter = Depends(get_currency_converter),
    session: Session = Depends(get_session),
) -> EmployeeService:
    """Provide the employee service with its repository, converter, and session."""
    return EmployeeService(
        reader=repository, writer=repository, converter=converter, session=session
    )


def get_analytics_service(session: Session = Depends(get_session)) -> AnalyticsService:
    """Provide the analytics service over a SQL analytics repository."""
    return AnalyticsService(SqlAnalyticsRepository(session), Currency(settings.base_currency))


def get_csv_service(
    repository: SqlEmployeeRepository = Depends(get_employee_repository),
    converter: CurrencyConverter = Depends(get_currency_converter),
    session: Session = Depends(get_session),
) -> EmployeeCsvService:
    """Provide the CSV import/export service."""
    return EmployeeCsvService(repository=repository, converter=converter, session=session)


def get_llm_client() -> LlmClient:
    """Provide the LLM client for the configured provider (Anthropic, Gemini, or stub)."""
    return build_llm_client(settings)


def get_qa_cache() -> dict[str, str]:
    """Provide the process-wide question->SQL cache (overridable in tests)."""
    return _QA_SQL_CACHE


def get_qa_service(
    client: LlmClient = Depends(get_llm_client),
    session: Session = Depends(get_session),
    cache: dict[str, str] = Depends(get_qa_cache),
) -> QaService:
    """Provide the natural-language Q&A service."""
    return QaService(client=client, session=session, cache=cache)
