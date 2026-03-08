"""Tests for services/technical_analysis.py."""

import pytest
import pandas as pd
import numpy as np
from services.technical_analysis import compute_indicators, get_signals, get_support_resistance


# Parametrized RSI boundary checks
@pytest.mark.parametrize("rsi,expected_signal", [
    (29.9, "BUY"),
    (30.0, "HOLD"),   # boundary: exactly 30 is not < 30
    (50.0, "HOLD"),
    (70.0, "HOLD"),   # boundary: exactly 70 is not > 70
    (70.1, "SELL"),
])
def test_rsi_signal_boundaries(rsi, expected_signal):
    df = pd.DataFrame({
        "RSI": [rsi, rsi],
        "Close": [100.0, 100.0],
        "BB_upper": [110.0, 110.0],
        "BB_lower": [90.0, 90.0],
        "MACD": [0.0, 0.0],
        "MACD_signal": [0.0, 0.0],
    })
    signals = get_signals(df)
    assert signals["RSI"][0] == expected_signal

INDICATOR_COLUMNS = ["SMA20", "SMA50", "EMA20", "BB_upper", "BB_mid", "BB_lower",
                      "RSI", "MACD", "MACD_signal", "MACD_hist"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_signals_df(rsi=50.0, macd=0.0, macd_signal=0.0,
                     macd_prev=0.0, macd_signal_prev=0.0,
                     close=100.0, bb_upper=110.0, bb_lower=90.0):
    """Two-row DataFrame with controlled indicator values for signal tests."""
    return pd.DataFrame({
        "Close": [close, close],
        "Open":  [close, close],
        "High":  [bb_upper, bb_upper],
        "Low":   [bb_lower, bb_lower],
        "Volume": [1_000_000, 1_000_000],
        "RSI":   [rsi, rsi],
        "MACD":  [macd_prev, macd],
        "MACD_signal": [macd_signal_prev, macd_signal],
        "MACD_hist":   [macd_prev - macd_signal_prev, macd - macd_signal],
        "BB_upper": [bb_upper, bb_upper],
        "BB_mid":   [100.0, 100.0],
        "BB_lower": [bb_lower, bb_lower],
    })


# ── compute_indicators ────────────────────────────────────────────────────────

class TestComputeIndicators:
    def test_empty_df_returned_unchanged(self):
        df = pd.DataFrame()
        result = compute_indicators(df)
        assert result.empty

    def test_too_short_returned_unchanged(self, ohlcv_factory):
        df = ohlcv_factory(n=19)
        result = compute_indicators(df)
        for col in INDICATOR_COLUMNS:
            assert col not in result.columns

    def test_all_indicator_columns_present(self, ohlcv_factory):
        df = ohlcv_factory(n=60)
        result = compute_indicators(df)
        for col in INDICATOR_COLUMNS:
            assert col in result.columns, f"Missing column: {col}"

    def test_sma20_last_value(self, ohlcv_factory):
        df = ohlcv_factory(n=60)
        result = compute_indicators(df)
        expected = df["Close"].iloc[-20:].mean()
        assert abs(result["SMA20"].iloc[-1] - expected) < 1e-8

    def test_original_df_not_mutated(self, ohlcv_factory):
        df = ohlcv_factory(n=60)
        original_cols = set(df.columns)
        compute_indicators(df)
        assert set(df.columns) == original_cols

    def test_rsi_values_in_valid_range(self, ohlcv_factory):
        df = ohlcv_factory(n=60)
        result = compute_indicators(df)
        rsi = result["RSI"].dropna()
        assert (rsi >= 0).all() and (rsi <= 100).all()

    def test_exactly_20_rows_runs_without_error(self, ohlcv_factory):
        df = ohlcv_factory(n=20)
        result = compute_indicators(df)
        # SMA20 last value should be non-NaN
        assert pd.notna(result["SMA20"].iloc[-1])

    def test_sma50_requires_50_rows(self, ohlcv_factory):
        df = ohlcv_factory(n=30)
        result = compute_indicators(df)
        # With only 30 rows, SMA50 should be all NaN
        assert result["SMA50"].isna().all()

    def test_bb_upper_above_lower(self, ohlcv_factory):
        df = ohlcv_factory(n=60)
        result = compute_indicators(df)
        valid = result[result["BB_upper"].notna() & result["BB_lower"].notna()]
        assert (valid["BB_upper"] >= valid["BB_lower"]).all()


# ── get_signals ───────────────────────────────────────────────────────────────

class TestGetSignals:
    def test_empty_df_returns_empty_dict(self):
        assert get_signals(pd.DataFrame()) == {}

    def test_rsi_oversold_gives_buy(self):
        df = _make_signals_df(rsi=25.0)
        signals = get_signals(df)
        assert signals["RSI"][0] == "BUY"
        assert "oversold" in signals["RSI"][1]

    def test_rsi_overbought_gives_sell(self):
        df = _make_signals_df(rsi=75.0)
        signals = get_signals(df)
        assert signals["RSI"][0] == "SELL"
        assert "overbought" in signals["RSI"][1]

    def test_rsi_neutral_gives_hold(self):
        df = _make_signals_df(rsi=50.0)
        signals = get_signals(df)
        assert signals["RSI"][0] == "HOLD"

    def test_macd_bullish_crossover_gives_buy(self):
        # Previous: MACD below signal; current: MACD above signal
        df = _make_signals_df(macd=0.2, macd_signal=0.1,
                               macd_prev=-0.1, macd_signal_prev=0.05)
        signals = get_signals(df)
        assert signals["MACD"][0] == "BUY"

    def test_macd_bearish_crossover_gives_sell(self):
        # Previous: MACD above signal; current: MACD below signal
        df = _make_signals_df(macd=-0.2, macd_signal=-0.1,
                               macd_prev=0.1, macd_signal_prev=-0.05)
        signals = get_signals(df)
        assert signals["MACD"][0] == "SELL"

    def test_macd_no_crossover_gives_hold(self):
        # Both bars: MACD above signal (no crossover)
        df = _make_signals_df(macd=0.5, macd_signal=0.1,
                               macd_prev=0.3, macd_signal_prev=0.1)
        signals = get_signals(df)
        assert signals["MACD"][0] == "HOLD"

    def test_bb_price_near_upper_gives_sell(self):
        # Position = (close - lower) / (upper - lower) >= 0.9
        df = _make_signals_df(close=109.0, bb_upper=110.0, bb_lower=90.0)
        signals = get_signals(df)
        assert signals["BB"][0] == "SELL"

    def test_bb_price_near_lower_gives_buy(self):
        # Position = (close - lower) / (upper - lower) <= 0.1
        df = _make_signals_df(close=91.0, bb_upper=110.0, bb_lower=90.0)
        signals = get_signals(df)
        assert signals["BB"][0] == "BUY"

    def test_bb_price_mid_gives_hold(self):
        df = _make_signals_df(close=100.0, bb_upper=110.0, bb_lower=90.0)
        signals = get_signals(df)
        assert signals["BB"][0] == "HOLD"

    def test_overall_key_always_present(self):
        df = _make_signals_df(rsi=50.0)
        signals = get_signals(df)
        assert "Overall" in signals

    def test_overall_reflects_majority_vote(self):
        # RSI=25 → BUY, BB near lower → BUY, MACD no crossover → HOLD
        df = _make_signals_df(
            rsi=25.0, close=91.0,
            bb_upper=110.0, bb_lower=90.0,
            macd=0.5, macd_signal=0.1,
            macd_prev=0.3, macd_signal_prev=0.1,
        )
        signals = get_signals(df)
        assert signals["Overall"][0] == "BUY"


# ── get_support_resistance ────────────────────────────────────────────────────

class TestGetSupportResistance:
    def test_empty_df_returns_empty_dict(self):
        assert get_support_resistance(pd.DataFrame()) == {}

    def test_too_short_returns_empty_dict(self, ohlcv_factory):
        df = ohlcv_factory(n=39)  # window=20 → needs 40 rows
        assert get_support_resistance(df, window=20) == {}

    def test_support_equals_low_of_last_2_windows(self, ohlcv_factory):
        df = ohlcv_factory(n=60)
        result = get_support_resistance(df, window=20)
        expected_support = float(df.tail(40)["Low"].min())
        assert abs(result["support"] - expected_support) < 1e-8

    def test_resistance_equals_high_of_last_2_windows(self, ohlcv_factory):
        df = ohlcv_factory(n=60)
        result = get_support_resistance(df, window=20)
        expected_resistance = float(df.tail(40)["High"].max())
        assert abs(result["resistance"] - expected_resistance) < 1e-8

    def test_support_below_resistance(self, ohlcv_factory):
        df = ohlcv_factory(n=60)
        result = get_support_resistance(df)
        assert result["support"] < result["resistance"]

    def test_custom_window(self, ohlcv_factory):
        df = ohlcv_factory(n=60)
        result = get_support_resistance(df, window=10)
        expected_support = float(df.tail(20)["Low"].min())
        assert abs(result["support"] - expected_support) < 1e-8
