"""Unit tests for the table-backed currency converter."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.currency import Currency
from app.domain.money import Money
from app.services.currency_converter import FxTableCurrencyConverter, MissingRateError

USD = Currency("USD")
EUR = Currency("EUR")
JPY = Currency("JPY")

# 1 EUR = 1.08 USD; 1 JPY = 0.0067 USD.
RATES = {"EUR": 1_080_000, "JPY": 6_700}


def make_converter() -> FxTableCurrencyConverter:
    return FxTableCurrencyConverter(RATES, USD)


def test_base_currency_is_returned_unchanged() -> None:
    money = Money(Decimal("100.00"), USD)

    assert make_converter().to_base(money) is money


def test_converts_eur_to_usd_at_the_table_rate() -> None:
    converted = make_converter().to_base(Money(Decimal("100.00"), EUR))

    assert converted.currency == USD
    assert converted.to_minor_units() == 108_00


def test_converts_zero_decimal_currency() -> None:
    converted = make_converter().to_base(Money(Decimal("1000000"), JPY))

    assert converted.currency == USD
    assert converted.to_minor_units() == 6_700_00


def test_missing_rate_raises() -> None:
    with pytest.raises(MissingRateError):
        make_converter().to_base(Money(Decimal("1.00"), Currency("GBP")))
