"""Tests for services/benchmark_service.py — pure computation, no DB or network."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from services.benchmark_service import compute_performance_stats, compute_benchmark_comparison


def _make_series(n=60, start=10000.0, end=12000.0):
    """Rising portfolio value series on business days."""
    dates = pd.bdate_range(end="2024-12-31", periods=n)
    values = np.linspace(start, end, n)
    return pd.Series(values, index=dates)


def _make_flat_series(n=60, value=10000.0):
    dates = pd.bdate_range(end="2024-12-31", periods=n)
    return pd.Series(np.full(n, value), index=dates)


class TestComputePerformanceStats:
    def test_empty_series_returns_empty_dict(self):
        assert compute_performance_stats(pd.Series(dtype=float)) == {}

    def test_single_element_returns_empty_dict(self):
        s = pd.Series([10000.0], index=pd.bdate_range("2024-01-01", periods=1))
        assert compute_performance_stats(s) == {}

    def test_flat_series_zero_return(self):
        stats = compute_performance_stats(_make_flat_series())
        assert abs(stats["Total Return (%)"] - 0.0) < 1e-6

    def test_flat_series_near_zero_volatility(self):
        stats = compute_performance_stats(_make_flat_series())
        assert abs(stats["Volatility (%)"]) < 1e-3

    def test_doubling_series_100_pct_return(self):
        s = _make_series(start=10000.0, end=20000.0)
        stats = compute_performance_stats(s)
        assert abs(stats["Total Return (%)"] - 100.0) < 1e-3

    def test_returns_all_expected_keys(self):
        stats = compute_performance_stats(_make_series())
        expected_keys = {"Total Return (%)", "Annualized Return (%)",
                         "Volatility (%)", "Sharpe Ratio", "Max Drawdown (%)"}
        assert expected_keys.issubset(stats.keys())

    def test_max_drawdown_is_negative_for_declining_series(self):
        # Series rises then falls back below start
        dates = pd.bdate_range(end="2024-12-31", periods=60)
        values = np.concatenate([np.linspace(10000, 15000, 30),
                                  np.linspace(15000, 8000, 30)])
        s = pd.Series(values, index=dates)
        stats = compute_performance_stats(s)
        assert stats["Max Drawdown (%)"] < 0

    def test_max_drawdown_is_zero_for_monotone_rising(self):
        stats = compute_performance_stats(_make_series(start=10000.0, end=20000.0))
        # Monotonically rising → drawdown = 0
        assert stats["Max Drawdown (%)"] >= -1e-6

    def test_annualized_return_approximately_correct(self):
        # ~20% total return over ~60 business days ≈ 3 months
        s = _make_series(n=60, start=10000.0, end=12000.0)
        stats = compute_performance_stats(s)
        assert stats["Annualized Return (%)"] > stats["Total Return (%)"]


class TestComputeBenchmarkComparison:
    def test_empty_portfolio_returns_empty_dict(self, ohlcv_factory):
        result = compute_benchmark_comparison(pd.Series(dtype=float), "SPY")
        assert result == {}

    @patch("services.benchmark_service.get_historical_prices_range")
    def test_returns_expected_keys(self, mock_hist, ohlcv_factory):
        bench_df = ohlcv_factory(n=60)
        mock_hist.return_value = bench_df
        portfolio_values = _make_series(n=60)
        # Align dates
        portfolio_values.index = bench_df.index

        result = compute_benchmark_comparison(portfolio_values, "SPY")
        assert "portfolio_norm" in result
        assert "benchmark_norm" in result
        assert "beta" in result
        assert "alpha" in result
        assert "correlation" in result
        assert "portfolio_stats" in result
        assert "benchmark_stats" in result

    @patch("services.benchmark_service.get_historical_prices_range")
    def test_normalized_series_start_at_100(self, mock_hist, ohlcv_factory):
        bench_df = ohlcv_factory(n=60)
        mock_hist.return_value = bench_df
        portfolio_values = _make_series(n=60)
        portfolio_values.index = bench_df.index

        result = compute_benchmark_comparison(portfolio_values, "SPY")
        assert abs(result["portfolio_norm"].iloc[0] - 100.0) < 1e-6
        assert abs(result["benchmark_norm"].iloc[0] - 100.0) < 1e-6

    @patch("services.benchmark_service.get_historical_prices_range")
    def test_empty_benchmark_returns_empty_dict(self, mock_hist):
        mock_hist.return_value = pd.DataFrame()
        portfolio_values = _make_series(n=60)
        result = compute_benchmark_comparison(portfolio_values, "SPY")
        assert result == {}

    @patch("services.benchmark_service.get_historical_prices_range")
    def test_benchmark_called_with_correct_ticker(self, mock_hist, ohlcv_factory):
        bench_df = ohlcv_factory(n=60)
        mock_hist.return_value = bench_df
        portfolio_values = _make_series(n=60)
        portfolio_values.index = bench_df.index

        compute_benchmark_comparison(portfolio_values, "QQQ")
        call_args = mock_hist.call_args
        assert call_args[0][0] == "QQQ"

    @patch("services.benchmark_service.get_historical_prices_range")
    def test_drawdown_series_present_in_result(self, mock_hist, ohlcv_factory):
        bench_df = ohlcv_factory(n=60)
        mock_hist.return_value = bench_df
        portfolio_values = _make_series(n=60)
        portfolio_values.index = bench_df.index

        result = compute_benchmark_comparison(portfolio_values, "SPY")
        assert "drawdown" in result
        assert isinstance(result["drawdown"], pd.Series)
