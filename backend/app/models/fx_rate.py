"""The ``FxRate`` ORM model — exchange rates used to normalize salaries to USD.

Rates are stored as **integer micro-USD per one unit of the currency** (e.g. 1 EUR =
1.08 USD is stored as ``1_080_000``). Integers keep the conversion exact and dialect-
portable; the micro scale gives six significant digits, plenty for salary comparison.
This table is the swappable rate source behind the ``CurrencyConverter`` protocol.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Scale: one unit of the currency equals (rate_to_usd_micros / MICROS_PER_USD) USD.
MICROS_PER_USD = 1_000_000


class FxRate(Base):
    """The exchange rate from one currency to USD.

    Attributes:
        currency: ISO 4217 code, primary key.
        rate_to_usd_micros: Micro-USD per one unit of ``currency``.
        updated_at: When the rate was last set.
    """

    __tablename__ = "fx_rates"

    currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    rate_to_usd_micros: Mapped[int] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
