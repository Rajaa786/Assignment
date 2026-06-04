"""Shared transport schemas: monetary amounts and cursor-paginated pages.

These Pydantic models are the wire shape. ``MoneyOut`` carries an exact decimal
amount plus its currency (never a float); ``Page`` is the standard list envelope —
``{ items, next_cursor, total }`` — used by every list endpoint (``ADR-0007``).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class MoneyOut(BaseModel):
    """A monetary amount on the wire: exact decimal value + ISO 4217 currency."""

    amount: Decimal = Field(description="Exact amount in major units (e.g. dollars).")
    currency: str = Field(description="ISO 4217 currency code.")
    minor_units: int = Field(description="Amount as integer minor units (e.g. cents).")


class Page(BaseModel, Generic[T]):
    """A single page of a cursor-paginated list.

    Attributes:
        items: The rows on this page.
        next_cursor: Opaque token to fetch the next page, or ``None`` at the end.
        total: Total rows matching the query across all pages.
    """

    items: list[T]
    next_cursor: str | None = Field(
        default=None, description="Opaque cursor for the next page; null if this is the last page."
    )
    total: int = Field(description="Total number of matching rows across all pages.")
