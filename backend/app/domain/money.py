"""The ``Money`` value object: exact, currency-aware monetary amounts.

Money is the single most important value in this domain, so it gets its own type
with three guarantees:

1. **Exact.** Amounts are :class:`~decimal.Decimal`, never ``float``. Persistence is
   integer minor units (cents), reconstructed losslessly via the currency exponent.
2. **Currency-safe.** Adding USD to EUR raises; currencies are never coerced silently.
3. **Immutable.** Every operation returns a new ``Money``.

This is why ``ADR-0006`` chooses integer minor units: the value object owns the
major⇄minor conversion so no caller ever does float math on money.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.currency import Currency


class CurrencyMismatchError(ValueError):
    """Raised when an operation mixes two different currencies."""


@dataclass(frozen=True, slots=True)
class Money:
    """An exact monetary amount in a specific currency.

    Attributes:
        amount: The value in major units (e.g. dollars), as an exact ``Decimal``.
        currency: The currency the amount is denominated in.
    """

    amount: Decimal
    currency: Currency

    def to_minor_units(self) -> int:
        """Return the amount as an integer number of minor units (e.g. cents).

        The amount is rounded to the currency's minor-unit precision (half-up) so
        the result is always a whole number of the smallest denomination.
        """
        quantum = Decimal(1).scaleb(-self.currency.minor_unit_digits)
        rounded = self.amount.quantize(quantum, rounding=ROUND_HALF_UP)
        return int(rounded * self.currency.minor_unit_factor)

    @classmethod
    def from_minor_units(cls, minor_units: int, currency: Currency) -> Money:
        """Build ``Money`` from an integer minor-unit amount and a currency.

        This is the inverse of :meth:`to_minor_units` and the canonical way to
        reconstruct money read from the database.
        """
        amount = Decimal(minor_units) / currency.minor_unit_factor
        return cls(amount=amount, currency=currency)

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(f"Cannot operate on {self.currency} and {other.currency}")

    def __add__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __lt__(self, other: Money) -> bool:
        self._require_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._require_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        self._require_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._require_same_currency(other)
        return self.amount >= other.amount

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"
