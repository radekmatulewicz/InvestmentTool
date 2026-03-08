"""Tests for utils/validators.py."""

import pytest
from unittest.mock import patch
from utils.validators import (
    is_valid_ticker_format,
    validate_ticker,
    validate_quantity,
    validate_price,
    validate_fees,
)


class TestIsValidTickerFormat:
    def test_simple_ticker(self):
        assert is_valid_ticker_format("AAPL") is True

    def test_with_dot(self):
        assert is_valid_ticker_format("BRK.B") is True

    def test_crypto_with_dash(self):
        assert is_valid_ticker_format("BTC-USD") is True

    def test_index_with_caret(self):
        assert is_valid_ticker_format("^GSPC") is True

    def test_empty_string(self):
        assert is_valid_ticker_format("") is False

    def test_too_long(self):
        assert is_valid_ticker_format("A" * 21) is False

    def test_with_space(self):
        assert is_valid_ticker_format("AP PL") is False

    def test_special_chars(self):
        assert is_valid_ticker_format("!BAD") is False

    def test_lowercase_normalised_to_uppercase(self):
        # Function strips and uppercases before regex, so lowercase is accepted
        assert is_valid_ticker_format("aapl") is True

    def test_single_char(self):
        assert is_valid_ticker_format("V") is True

    def test_exactly_20_chars(self):
        assert is_valid_ticker_format("A" * 20) is True


class TestValidateTicker:
    @patch("utils.validators._validate_ticker", return_value=True)
    def test_valid_ticker(self, mock_vt):
        ok, msg = validate_ticker("AAPL")
        assert ok is True
        assert msg == ""
        mock_vt.assert_called_once_with("AAPL")

    @patch("utils.validators._validate_ticker", return_value=True)
    def test_lowercase_input_normalised(self, mock_vt):
        ok, msg = validate_ticker("aapl")
        assert ok is True
        mock_vt.assert_called_once_with("AAPL")

    @patch("utils.validators._validate_ticker", return_value=False)
    def test_ticker_not_found(self, mock_vt):
        ok, msg = validate_ticker("XYZ")
        assert ok is False
        assert "XYZ" in msg

    def test_bad_format_skips_network_call(self):
        # Should fail before ever calling _validate_ticker
        ok, msg = validate_ticker("!BAD")
        assert ok is False
        assert msg == "Invalid ticker format"

    @patch("utils.validators._validate_ticker", side_effect=RuntimeError("network error"))
    def test_exception_returns_error_message(self, mock_vt):
        ok, msg = validate_ticker("AAPL")
        assert ok is False
        assert "network error" in msg

    @patch("utils.validators._validate_ticker", return_value=True)
    def test_whitespace_stripped(self, mock_vt):
        ok, msg = validate_ticker("  AAPL  ")
        assert ok is True
        mock_vt.assert_called_once_with("AAPL")


class TestValidateQuantity:
    def test_integer(self):
        assert validate_quantity(10) == (True, "")

    def test_float(self):
        assert validate_quantity(0.5) == (True, "")

    def test_string_number(self):
        assert validate_quantity("10.5") == (True, "")

    def test_zero_fails(self):
        ok, msg = validate_quantity(0)
        assert ok is False
        assert "greater than 0" in msg

    def test_negative_fails(self):
        ok, msg = validate_quantity(-1)
        assert ok is False

    def test_non_numeric_string_fails(self):
        ok, msg = validate_quantity("abc")
        assert ok is False
        assert "number" in msg

    def test_very_small_positive(self):
        assert validate_quantity(0.00001) == (True, "")


class TestValidatePrice:
    def test_valid_price(self):
        assert validate_price(150.0) == (True, "")

    def test_zero_fails(self):
        ok, msg = validate_price(0)
        assert ok is False
        assert "greater than 0" in msg

    def test_negative_fails(self):
        ok, msg = validate_price(-50)
        assert ok is False

    def test_string_number(self):
        assert validate_price("99.99") == (True, "")

    def test_non_numeric_fails(self):
        ok, msg = validate_price("free")
        assert ok is False
        assert "number" in msg


class TestValidateFees:
    def test_zero_is_valid(self):
        assert validate_fees(0) == (True, "")

    def test_positive_is_valid(self):
        assert validate_fees(9.99) == (True, "")

    def test_negative_fails(self):
        ok, msg = validate_fees(-1)
        assert ok is False
        assert "negative" in msg

    def test_string_number(self):
        assert validate_fees("4.95") == (True, "")

    def test_non_numeric_fails(self):
        ok, msg = validate_fees("free")
        assert ok is False
        assert "number" in msg
