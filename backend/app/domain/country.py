"""The ``Country`` value object and the countries this org operates in.

A country is a validated ISO 3166-1 alpha-2 code that also knows its default payroll
currency, so employee records can derive currency from country instead of letting the
two drift out of sync.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.currency import Currency

# ISO 3166-1 alpha-2 -> (display name, default ISO 4217 currency). The org's
# payroll countries; extend alongside `currency._SUPPORTED` when adding one.
_COUNTRIES: dict[str, tuple[str, str]] = {
    "US": ("United States", "USD"),
    "GB": ("United Kingdom", "GBP"),
    "DE": ("Germany", "EUR"),
    "FR": ("France", "EUR"),
    "IN": ("India", "INR"),
    "JP": ("Japan", "JPY"),
    "CA": ("Canada", "CAD"),
    "AU": ("Australia", "AUD"),
    "SG": ("Singapore", "SGD"),
    "BR": ("Brazil", "BRL"),
    "AE": ("United Arab Emirates", "AED"),
    "ZA": ("South Africa", "ZAR"),
}


class InvalidCountryError(ValueError):
    """Raised when a country code is not a supported ISO 3166-1 alpha-2 code."""


@dataclass(frozen=True, slots=True)
class Country:
    """An ISO 3166-1 alpha-2 country code.

    Attributes:
        code: The two-letter uppercase country code (e.g. ``"US"``).
    """

    code: str

    def __post_init__(self) -> None:
        if self.code not in _COUNTRIES:
            raise InvalidCountryError(f"Unsupported country code: {self.code!r}")

    @property
    def display_name(self) -> str:
        """Human-readable country name for the UI."""
        return _COUNTRIES[self.code][0]

    @property
    def default_currency(self) -> Currency:
        """The currency employees in this country are paid in by default."""
        return Currency(_COUNTRIES[self.code][1])

    def __str__(self) -> str:
        return self.code


def supported_country_codes() -> tuple[str, ...]:
    """Return the sorted tuple of supported ISO 3166-1 alpha-2 codes."""
    return tuple(sorted(_COUNTRIES))
