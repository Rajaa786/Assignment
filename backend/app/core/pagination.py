"""Opaque cursor encoding for keyset pagination.

A cursor is a base64url token wrapping the sort key and id of the last row on the
previous page: ``{"k": <sort_value>, "id": <last_id>}``. Keyset pagination
(``WHERE (sort, id) > (k, last_id)``) gives stable pages over 10k rows with no deep-
offset scans (``ADR-0007``). The token is opaque to clients — they pass it back
verbatim, never construct it.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Literal

SortDirection = Literal["asc", "desc"]


class InvalidCursorError(ValueError):
    """Raised when a cursor token is malformed or cannot be decoded."""


def encode_cursor(sort_value: str | int, last_id: int) -> str:
    """Encode the last row's sort value and id into an opaque cursor token.

    Args:
        sort_value: The value of the sort column for the last row on the page.
            Dates are passed as ISO strings so the token stays JSON-serializable.
        last_id: The primary key of the last row, used as a stable tiebreaker.

    Returns:
        A base64url-encoded token safe to place in a query string.
    """
    payload = json.dumps({"k": sort_value, "id": last_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[str | int, int]:
    """Decode a cursor token back into its sort value and id.

    Args:
        cursor: A token previously produced by :func:`encode_cursor`.

    Returns:
        A ``(sort_value, last_id)`` tuple.

    Raises:
        InvalidCursorError: If the token is not valid base64 or not the expected shape.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        data = json.loads(raw)
        return data["k"], int(data["id"])
    except (binascii.Error, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise InvalidCursorError("Malformed pagination cursor.") from exc
