"""
Tests for the holdings calculation logic in services/portfolio_service.py.

Strategy:
- Each test gets its own in-memory SQLite DB (via engine_per_test fixture).
- Data is committed so that get_holdings() — which opens its own session — can
  see it when its internal get_session() is patched to use the same engine.
- get_current_price is patched to avoid all yfinance calls.
"""

import pytest
import pandas as pd
from datetime import date
from decimal import Decimal
from contextlib import contextmanager
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Portfolio, Instrument, Transaction
from services.portfolio_service import (
    get_holdings,
    get_portfolio_summary,
    _detect_asset_type,
)


# ── Per-test isolated DB ──────────────────────────────────────────────────────

@pytest.fixture
def isolated_db():
    """
    Yields (session, get_session_fn) backed by a fresh in-memory SQLite DB.
    Data committed to `session` is visible to sessions returned by get_session_fn.
    """
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    session = Session()
    yield session, lambda: Session()
    session.close()


def _add_tx(session, portfolio_id, instrument_id, tx_type, qty, price,
            fees=0.0, tx_date=None):
    tx = Transaction(
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        transaction_type=tx_type,
        quantity=Decimal(str(qty)),
        price_per_unit=Decimal(str(price)),
        fees=Decimal(str(fees)),
        transaction_date=tx_date or date(2024, 1, 10),
    )
    session.add(tx)


@contextmanager
def _patch_services(get_session_fn, mock_prices: dict):
    """
    Patch get_session (in portfolio_service) and get_current_price.
    get_session_fn is called fresh each time, matching real service behavior.
    """
    with patch("services.portfolio_service.get_current_price",
               side_effect=lambda t: mock_prices.get(t, 0.0)), \
         patch("services.portfolio_service.get_session", side_effect=get_session_fn):
        yield


# ── _detect_asset_type ────────────────────────────────────────────────────────

class TestDetectAssetType:
    def test_etf(self):
        assert _detect_asset_type({"quoteType": "ETF"}) == "etf"

    def test_etf_case_insensitive(self):
        assert _detect_asset_type({"quoteType": "etf"}) == "etf"

    def test_crypto(self):
        assert _detect_asset_type({"quoteType": "cryptocurrency"}) == "crypto"

    def test_equity(self):
        assert _detect_asset_type({"quoteType": "EQUITY"}) == "stock"

    def test_empty_info_defaults_to_stock(self):
        assert _detect_asset_type({}) == "stock"


# ── get_holdings ──────────────────────────────────────────────────────────────

class TestGetHoldings:
    def test_empty_portfolio_returns_empty_df(self, isolated_db):
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="EmptyPort")
        session.add(portfolio)
        session.commit()

        with _patch_services(get_session_fn, {}):
            result = get_holdings(portfolio.id)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_single_buy_columns_and_values(self, isolated_db):
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="P1")
        instrument = Instrument(ticker="AAPL", name="Apple Inc.", asset_type="stock", currency="USD")
        session.add_all([portfolio, instrument])
        session.flush()
        _add_tx(session, portfolio.id, instrument.id, "buy", qty=10, price=100.0, fees=0.0)
        session.commit()

        with _patch_services(get_session_fn, {"AAPL": 150.0}):
            df = get_holdings(portfolio.id)

        assert len(df) == 1
        row = df.iloc[0]
        assert row["ticker"] == "AAPL"
        assert abs(row["quantity"] - 10.0) < 1e-8
        assert abs(row["avg_cost"] - 100.0) < 1e-8
        assert abs(row["current_price"] - 150.0) < 1e-8
        assert abs(row["current_value"] - 1500.0) < 1e-8
        assert abs(row["cost_basis"] - 1000.0) < 1e-8
        assert abs(row["unrealized_pnl"] - 500.0) < 1e-8

    def test_avg_cost_includes_fees(self, isolated_db):
        """
        Buy 10 @ $100 + $5 fee, then 5 @ $120 + $5 fee.
        buy_cost = (10*100 + 5) + (5*120 + 5) = 1005 + 605 = 1610
        buy_qty  = 15
        avg_cost = 1610 / 15 ≈ 107.333...
        """
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="P2")
        instrument = Instrument(ticker="AAPL", name="Apple", asset_type="stock", currency="USD")
        session.add_all([portfolio, instrument])
        session.flush()
        _add_tx(session, portfolio.id, instrument.id, "buy", qty=10, price=100.0, fees=5.0)
        _add_tx(session, portfolio.id, instrument.id, "buy", qty=5, price=120.0, fees=5.0)
        session.commit()

        with _patch_services(get_session_fn, {"AAPL": 150.0}):
            df = get_holdings(portfolio.id)

        expected_avg_cost = 1610.0 / 15.0
        assert abs(df.iloc[0]["avg_cost"] - expected_avg_cost) < 1e-6

    def test_sell_reduces_quantity(self, isolated_db):
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="P3")
        instrument = Instrument(ticker="AAPL", name="Apple", asset_type="stock", currency="USD")
        session.add_all([portfolio, instrument])
        session.flush()
        _add_tx(session, portfolio.id, instrument.id, "buy", qty=10, price=100.0)
        _add_tx(session, portfolio.id, instrument.id, "sell", qty=3, price=110.0)
        session.commit()

        with _patch_services(get_session_fn, {"AAPL": 150.0}):
            df = get_holdings(portfolio.id)

        assert abs(df.iloc[0]["quantity"] - 7.0) < 1e-8

    def test_full_sell_excludes_position(self, isolated_db):
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="P4")
        instrument = Instrument(ticker="AAPL", name="Apple", asset_type="stock", currency="USD")
        session.add_all([portfolio, instrument])
        session.flush()
        _add_tx(session, portfolio.id, instrument.id, "buy", qty=10, price=100.0)
        _add_tx(session, portfolio.id, instrument.id, "sell", qty=10, price=110.0)
        session.commit()

        with _patch_services(get_session_fn, {"AAPL": 150.0}):
            df = get_holdings(portfolio.id)

        assert df.empty

    def test_weight_pct_sums_to_100(self, isolated_db):
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="P5")
        aapl = Instrument(ticker="AAPL", name="Apple", asset_type="stock", currency="USD")
        msft = Instrument(ticker="MSFT", name="Microsoft", asset_type="stock", currency="USD")
        session.add_all([portfolio, aapl, msft])
        session.flush()
        _add_tx(session, portfolio.id, aapl.id, "buy", qty=10, price=100.0)
        _add_tx(session, portfolio.id, msft.id, "buy", qty=5, price=200.0)
        session.commit()

        with _patch_services(get_session_fn, {"AAPL": 150.0, "MSFT": 300.0}):
            df = get_holdings(portfolio.id)

        assert abs(df["weight_pct"].sum() - 100.0) < 1e-6

    def test_sorted_by_value_descending(self, isolated_db):
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="P6")
        cheap = Instrument(ticker="CHEAP", name="Cheap", asset_type="stock", currency="USD")
        pricey = Instrument(ticker="PRICEY", name="Pricey", asset_type="stock", currency="USD")
        session.add_all([portfolio, cheap, pricey])
        session.flush()
        _add_tx(session, portfolio.id, cheap.id, "buy", qty=1, price=10.0)
        _add_tx(session, portfolio.id, pricey.id, "buy", qty=1, price=500.0)
        session.commit()

        with _patch_services(get_session_fn, {"CHEAP": 10.0, "PRICEY": 500.0}):
            df = get_holdings(portfolio.id)

        assert df.iloc[0]["ticker"] == "PRICEY"
        assert df.iloc[1]["ticker"] == "CHEAP"

    def test_zero_price_no_error(self, isolated_db):
        """Price = 0 → current_value = 0, pnl_pct = -100% (full loss). No crash."""
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="P7")
        instrument = Instrument(ticker="AAPL", name="Apple", asset_type="stock", currency="USD")
        session.add_all([portfolio, instrument])
        session.flush()
        _add_tx(session, portfolio.id, instrument.id, "buy", qty=10, price=100.0)
        session.commit()

        with _patch_services(get_session_fn, {"AAPL": 0.0}):
            df = get_holdings(portfolio.id)

        assert abs(df.iloc[0]["current_value"] - 0.0) < 1e-8
        assert abs(df.iloc[0]["pnl_pct"] - (-100.0)) < 1e-6

    def test_multiple_tickers(self, isolated_db):
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="P8")
        aapl = Instrument(ticker="AAPL", name="Apple", asset_type="stock", currency="USD")
        msft = Instrument(ticker="MSFT", name="Microsoft", asset_type="stock", currency="USD")
        session.add_all([portfolio, aapl, msft])
        session.flush()
        _add_tx(session, portfolio.id, aapl.id, "buy", qty=5, price=100.0)
        _add_tx(session, portfolio.id, msft.id, "buy", qty=3, price=200.0)
        session.commit()

        with _patch_services(get_session_fn, {"AAPL": 120.0, "MSFT": 250.0}):
            df = get_holdings(portfolio.id)

        assert len(df) == 2
        assert set(df["ticker"]) == {"AAPL", "MSFT"}


# ── get_portfolio_summary ─────────────────────────────────────────────────────

class TestGetPortfolioSummary:
    def test_empty_portfolio_returns_zeros(self, isolated_db):
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="Zero")
        session.add(portfolio)
        session.commit()

        with _patch_services(get_session_fn, {}):
            summary = get_portfolio_summary(portfolio.id)

        assert summary["total_value"] == 0
        assert summary["total_cost"] == 0
        assert summary["unrealized_pnl"] == 0
        assert summary["unrealized_pnl_pct"] == 0
        assert summary["num_positions"] == 0

    def test_populated_portfolio_values(self, isolated_db):
        """
        10 AAPL @ $100 cost (no fees), current price $150.
        total_cost=1000, total_value=1500, pnl=500, pnl_pct=50%.
        """
        session, get_session_fn = isolated_db
        portfolio = Portfolio(name="Populated")
        instrument = Instrument(ticker="AAPL", name="Apple", asset_type="stock", currency="USD")
        session.add_all([portfolio, instrument])
        session.flush()
        _add_tx(session, portfolio.id, instrument.id, "buy", qty=10, price=100.0, fees=0.0)
        session.commit()

        with _patch_services(get_session_fn, {"AAPL": 150.0}):
            summary = get_portfolio_summary(portfolio.id)

        assert abs(summary["total_value"] - 1500.0) < 1e-6
        assert abs(summary["total_cost"] - 1000.0) < 1e-6
        assert abs(summary["unrealized_pnl"] - 500.0) < 1e-6
        assert abs(summary["unrealized_pnl_pct"] - 50.0) < 1e-6
        assert summary["num_positions"] == 1
