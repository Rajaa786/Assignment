"""Unit tests for the opaque cursor codec."""

from __future__ import annotations

import pytest

from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor


def test_cursor_round_trips_integer_sort_value() -> None:
    token = encode_cursor(500_00, 42)

    assert decode_cursor(token) == (500_00, 42)


def test_cursor_round_trips_string_sort_value() -> None:
    token = encode_cursor("Nguyen", 1001)

    assert decode_cursor(token) == ("Nguyen", 1001)


def test_cursor_is_opaque_not_plaintext() -> None:
    token = encode_cursor(123, 7)

    assert "123" not in token


def test_malformed_cursor_raises() -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor("not-a-valid-cursor!!")
