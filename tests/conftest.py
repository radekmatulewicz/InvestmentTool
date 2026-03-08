"""
conftest.py — session-level setup for the Investment Tool test suite.

The Streamlit cache decorators (@st.cache_data, @st.cache_resource) fail when
called outside a running Streamlit server. We replace them with no-ops BEFORE
any project module is imported so that decorated functions become plain functions
during the test run.
"""

import streamlit as st


def _noop_cache_data(*args, **kwargs):
    """Handles both @st.cache_data and @st.cache_data(ttl=...) call styles."""
    if kwargs or not args:
        # Called as @st.cache_data(ttl=900) → return a no-op decorator
        return lambda fn: fn
    fn = args[0]
    if callable(fn):
        # Called as @st.cache_data directly with the function
        return fn
    return lambda f: f


st.cache_data = _noop_cache_data
st.cache_resource = lambda fn: fn

# ── Project imports (after Streamlit patch is applied) ────────────────────────
import pytest
import pandas as pd
import numpy as np
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Portfolio, Instrument, Transaction


# ── In-memory SQLite engine (session-scoped — created once per test run) ──────
@pytest.fixture(scope="session")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="session")
def SessionFactory(engine):
    return sessionmaker(bind=engine)


# ── Per-test DB session with rollback isolation ───────────────────────────────
@pytest.fixture
def db_session(engine, SessionFactory):
    """Each test gets a transaction that is rolled back afterwards."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionFactory(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ── OHLCV DataFrame factory ───────────────────────────────────────────────────
@pytest.fixture
def ohlcv_factory():
    """Returns a helper that produces a realistic OHLCV DataFrame."""
    def _make(n=60, base_price=100.0, seed=42):
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range(end="2024-12-31", periods=n)
        close = base_price + np.cumsum(rng.normal(0, 1, n))
        close = np.maximum(close, 1.0)
        high = close * (1 + rng.uniform(0, 0.02, n))
        low = close * (1 - rng.uniform(0, 0.02, n))
        open_ = close * (1 + rng.normal(0, 0.005, n))
        volume = rng.integers(1_000_000, 10_000_000, n)
        return pd.DataFrame(
            {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
            index=dates,
        )
    return _make
