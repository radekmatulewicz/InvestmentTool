"""Tests for utils/formatting.py — pure functions, no fixtures needed."""

import pytest
from utils.formatting import fmt_currency, fmt_pct, fmt_number, pnl_color, fmt_metric_value


# Parametrized edge-case table for fmt_currency
@pytest.mark.parametrize("value,expected", [
    (0, "$0.00"),
    (999, "$999.00"),
    (1_000, "$1,000.00"),
    (1_000_000, "$1.00M"),
    (1_000_000_000, "$1.00B"),
    (1_000_000_000_000, "$1.00T"),
    (None, "N/A"),
])
def test_fmt_currency_parametrized(value, expected):
    assert fmt_currency(value) == expected


class TestFmtCurrency:
    def test_normal_value(self):
        assert fmt_currency(1234.5) == "$1,234.50"

    def test_millions(self):
        assert fmt_currency(2_500_000) == "$2.50M"

    def test_billions(self):
        assert fmt_currency(1_200_000_000) == "$1.20B"

    def test_trillions(self):
        assert fmt_currency(3e12) == "$3.00T"

    def test_none_returns_na(self):
        assert fmt_currency(None) == "N/A"

    def test_invalid_string_returns_na(self):
        assert fmt_currency("bad") == "N/A"

    def test_negative_value(self):
        result = fmt_currency(-500)
        assert "$" in result
        assert "-" in result

    def test_negative_millions(self):
        result = fmt_currency(-2_500_000)
        assert "M" in result
        assert "-" in result

    def test_custom_currency_symbol(self):
        assert fmt_currency(100, currency="€") == "€100.00"

    def test_custom_decimals(self):
        assert fmt_currency(100, decimals=0) == "$100"

    def test_zero(self):
        assert fmt_currency(0) == "$0.00"

    def test_small_positive(self):
        assert fmt_currency(0.005) == "$0.01"


class TestFmtPct:
    def test_normal(self):
        assert fmt_pct(12.345) == "12.35%"

    def test_none_returns_na(self):
        assert fmt_pct(None) == "N/A"

    def test_zero_decimals(self):
        assert fmt_pct(5.0, decimals=0) == "5%"

    def test_negative(self):
        assert fmt_pct(-3.5) == "-3.50%"

    def test_zero(self):
        assert fmt_pct(0) == "0.00%"

    def test_invalid_returns_na(self):
        assert fmt_pct("bad") == "N/A"


class TestFmtNumber:
    def test_large_number_with_comma(self):
        assert fmt_number(1_234_567.89) == "1,234,567.89"

    def test_none_returns_na(self):
        assert fmt_number(None) == "N/A"

    def test_zero(self):
        assert fmt_number(0) == "0.00"

    def test_custom_decimals(self):
        assert fmt_number(3.14159, decimals=4) == "3.1416"

    def test_invalid_returns_na(self):
        assert fmt_number("abc") == "N/A"


class TestPnlColor:
    def test_positive_is_green(self):
        assert pnl_color(10) == "green"

    def test_zero_is_green(self):
        assert pnl_color(0) == "green"

    def test_negative_is_red(self):
        assert pnl_color(-1) == "red"

    def test_invalid_is_gray(self):
        assert pnl_color("bad") == "gray"

    def test_float_positive(self):
        assert pnl_color(0.001) == "green"

    def test_float_negative(self):
        assert pnl_color(-0.001) == "red"


class TestFmtMetricValue:
    def test_currency_type(self):
        assert fmt_metric_value(1000, "currency") == "$1,000.00"

    def test_pct_type(self):
        assert fmt_metric_value(5.5, "pct") == "5.50%"

    def test_number_type(self):
        assert fmt_metric_value(42.0, "number") == "42.00"

    def test_unknown_type_returns_str(self):
        assert fmt_metric_value(99, "other") == "99"

    def test_none_unknown_type_returns_na(self):
        assert fmt_metric_value(None, "other") == "N/A"
