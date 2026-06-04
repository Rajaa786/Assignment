"""Table-backed implementation of the ``CurrencyConverter`` protocol.

Converts any supported currency to the base currency (USD) using integer micro-USD
rates loaded from the ``fx_rates`` table. The rates are passed in as a plain mapping,
so this class is pure and trivially testable; the FastAPI dependency builds it from
the database per request. Swapping in a live-rate source means a different builder,
not a different converter (Open/Closed; ``ADR-0006``).
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from app.domain.currency import Currency
from app.domain.money import Money
from app.models.fx_rate import MICROS_PER_USD


class MissingRateError(ValueError):
    """Raised when no exchange rate is available for a currency."""


class FxTableCurrencyConverter:
    """Normalizes money to a base currency using a fixed table of rates.

    Attributes:
        base_currency: The currency every amount is converted to.
    """

    def __init__(self, rates_to_usd_micros: Mapping[str, int], base_currency: Currency) -> None:
        """Initialize the converter.

        Args:
            rates_to_usd_micros: Map of ISO 4217 code to micro-USD per one unit.
            base_currency: The base currency (typically USD).
        """
        self._rates = dict(rates_to_usd_micros)
        self.base_currency = base_currency

    def to_base(self, money: Money) -> Money:
        """Convert ``money`` into the base currency.

        Args:
            money: An amount in any supported currency.

        Returns:
            The equivalent amount in the base currency. The base currency is
            returned unchanged; other currencies are scaled by their micro-USD rate.

        Raises:
            MissingRateError: If no rate is configured for the source currency.
        """
        if money.currency == self.base_currency:
            return money
        micros = self._rates.get(money.currency.code)
        if micros is None:
            raise MissingRateError(f"No exchange rate for {money.currency.code}")
        base_amount = money.amount * Decimal(micros) / Decimal(MICROS_PER_USD)
        return Money(base_amount, self.base_currency)
