"""The ``Currency`` value object and the set of currencies this system supports.

A currency is more than a string: it carries its **minor-unit exponent** (how many
decimal places it has), which is what makes exact integer-minor-unit money possible.
USD and most currencies have 2 (cents); JPY has 0 (no sub-unit); some Gulf currencies
have 3. Storing money as minor units is meaningless without knowing this exponent,
so it lives on the currency, not scattered through the code.
"""

from __future__ import annotations

from dataclasses import dataclass

# ISO 4217 code -> number of minor-unit decimal places. Limited to the currencies
# the org actually pays in; extend here when a new payroll country is added.
_SUPPORTED: dict[str, int] = {
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "INR": 2,
    "CAD": 2,
    "AUD": 2,
    "SGD": 2,
    "BRL": 2,
    "AED": 2,
    "ZAR": 2,
    "JPY": 0,  # zero-decimal currency — exercises the exponent logic
}


class InvalidCurrencyError(ValueError):
    """Raised when a currency code is not a supported ISO 4217 code."""


@dataclass(frozen=True, slots=True)
class Currency:
    """An ISO 4217 currency code with its minor-unit exponent.

    Attributes:
        code: The three-letter uppercase ISO 4217 code (e.g. ``"USD"``).
    """

    code: str

    def __post_init__(self) -> None:
        if self.code not in _SUPPORTED:
            raise InvalidCurrencyError(f"Unsupported currency code: {self.code!r}")

    @property
    def minor_unit_digits(self) -> int:
        """Number of decimal places in this currency's minor unit (2 for USD, 0 for JPY)."""
        return _SUPPORTED[self.code]

    @property
    def minor_unit_factor(self) -> int:
        """Multiplier between major and minor units (100 for USD, 1 for JPY)."""
        return int(10**self.minor_unit_digits)

    def __str__(self) -> str:
        return self.code


def supported_currency_codes() -> tuple[str, ...]:
    """Return the sorted tuple of supported ISO 4217 codes."""
    return tuple(sorted(_SUPPORTED))
