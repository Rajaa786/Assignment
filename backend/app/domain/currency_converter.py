"""The ``CurrencyConverter`` abstraction for normalizing money to a base currency.

Comparing salaries across countries requires converting every amount to one base
currency (USD). *How* rates are sourced — a seeded table now, a live feed later — is
a detail behind this ``Protocol``. Services depend on the protocol, not a concrete
implementation, so the rate source can be swapped without touching call sites
(Open/Closed; ``ADR-0006``).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.money import Money


@runtime_checkable
class CurrencyConverter(Protocol):
    """Converts monetary amounts into the system's base currency."""

    def to_base(self, money: Money) -> Money:
        """Convert ``money`` into the base currency.

        Args:
            money: An amount in any supported currency.

        Returns:
            The equivalent amount in the base currency, rounded to that currency's
            minor unit.
        """
        ...
