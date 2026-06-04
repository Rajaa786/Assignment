"""Unit tests for the ``Currency`` and ``Country`` value objects."""

from __future__ import annotations

import pytest

from app.domain.country import Country, InvalidCountryError
from app.domain.currency import Currency, InvalidCurrencyError


def test_two_decimal_currency_reports_exponent_and_factor() -> None:
    usd = Currency("USD")

    assert usd.minor_unit_digits == 2
    assert usd.minor_unit_factor == 100


def test_zero_decimal_currency_reports_no_minor_unit() -> None:
    jpy = Currency("JPY")

    assert jpy.minor_unit_digits == 0
    assert jpy.minor_unit_factor == 1


def test_unsupported_currency_is_rejected() -> None:
    with pytest.raises(InvalidCurrencyError):
        Currency("XYZ")


def test_country_exposes_display_name_and_default_currency() -> None:
    country = Country("US")

    assert country.display_name == "United States"
    assert country.default_currency == Currency("USD")


def test_country_default_currency_can_be_zero_decimal() -> None:
    assert Country("JP").default_currency == Currency("JPY")


def test_unsupported_country_is_rejected() -> None:
    with pytest.raises(InvalidCountryError):
        Country("XX")
