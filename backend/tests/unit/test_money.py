"""Unit tests for the ``Money`` value object — exactness, currency safety, immutability."""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from app.domain.currency import Currency
from app.domain.money import CurrencyMismatchError, Money

USD = Currency("USD")
EUR = Currency("EUR")
JPY = Currency("JPY")


def test_from_minor_units_reconstructs_major_amount() -> None:
    money = Money.from_minor_units(123_45, USD)

    assert money.amount == Decimal("123.45")
    assert money.currency == USD


def test_to_minor_units_returns_whole_cents() -> None:
    money = Money(Decimal("123.45"), USD)

    assert money.to_minor_units() == 12345


def test_to_minor_units_rounds_half_up() -> None:
    assert Money(Decimal("1.005"), USD).to_minor_units() == 101


def test_zero_decimal_currency_has_no_minor_unit_split() -> None:
    money = Money.from_minor_units(5000, JPY)

    assert money.amount == Decimal("5000")
    assert money.to_minor_units() == 5000


def test_minor_units_round_trip_is_lossless() -> None:
    original = Money.from_minor_units(987_654, USD)

    assert Money.from_minor_units(original.to_minor_units(), USD) == original


def test_adding_same_currency_sums_amounts() -> None:
    assert Money(Decimal("10.00"), USD) + Money(Decimal("5.50"), USD) == Money(
        Decimal("15.50"), USD
    )


def test_subtracting_same_currency_subtracts_amounts() -> None:
    assert Money(Decimal("10.00"), USD) - Money(Decimal("4.00"), USD) == Money(Decimal("6.00"), USD)


def test_adding_different_currencies_raises() -> None:
    with pytest.raises(CurrencyMismatchError):
        _ = Money(Decimal("10.00"), USD) + Money(Decimal("10.00"), EUR)


def test_comparing_same_currency_orders_by_amount() -> None:
    assert Money(Decimal("1.00"), USD) < Money(Decimal("2.00"), USD)
    assert Money(Decimal("2.00"), USD) >= Money(Decimal("2.00"), USD)


def test_comparing_different_currencies_raises() -> None:
    with pytest.raises(CurrencyMismatchError):
        _ = Money(Decimal("1.00"), USD) < Money(Decimal("2.00"), EUR)


def test_money_is_immutable() -> None:
    money = Money(Decimal("1.00"), USD)

    with pytest.raises(dataclasses.FrozenInstanceError):
        money.amount = Decimal("2.00")  # type: ignore[misc]
