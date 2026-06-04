"""Data access for exchange rates.

A narrow reader the currency converter depends on: it returns the whole (small) rate
table as a mapping, which is all the converter needs to normalize salaries to USD.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fx_rate import FxRate


class FxRateReader(Protocol):
    """Reads exchange rates."""

    def rates_to_usd_micros(self) -> dict[str, int]:
        """Return a map of ISO 4217 code to micro-USD per one unit of that currency."""
        ...


class SqlFxRateRepository:
    """SQLAlchemy-backed :class:`FxRateReader`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def rates_to_usd_micros(self) -> dict[str, int]:
        """Load all exchange rates as a ``{currency: micro_usd}`` mapping."""
        rows = self._session.scalars(select(FxRate)).all()
        return {row.currency: row.rate_to_usd_micros for row in rows}
