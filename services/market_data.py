import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import CACHE_TTL_SECONDS


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_current_price(ticker: str) -> float | None:
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        price = getattr(info, "last_price", None)
        if price is None:
            hist = t.history(period="2d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        return float(price) if price else None
    except Exception:
        return None


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_ticker_info(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return info if info else {}
    except Exception:
        return {}


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_historical_prices(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, auto_adjust=True)
        if hist.empty:
            return pd.DataFrame()
        hist.index = pd.to_datetime(hist.index).tz_localize(None)
        return hist
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_historical_prices_range(ticker: str, start: str, end: str) -> pd.DataFrame:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=start, end=end, auto_adjust=True)
        if hist.empty:
            return pd.DataFrame()
        hist.index = pd.to_datetime(hist.index).tz_localize(None)
        return hist
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def validate_ticker(ticker: str) -> bool:
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        price = getattr(info, "last_price", None)
        return price is not None and float(price) > 0
    except Exception:
        return False


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_ticker_name(ticker: str) -> str:
    try:
        info = get_ticker_info(ticker)
        return info.get("longName") or info.get("shortName") or ticker
    except Exception:
        return ticker


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_financials(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        return {
            "income_stmt_annual": t.financials,
            "income_stmt_quarterly": t.quarterly_financials,
            "balance_sheet_annual": t.balance_sheet,
            "balance_sheet_quarterly": t.quarterly_balance_sheet,
            "cash_flow_annual": t.cashflow,
            "cash_flow_quarterly": t.quarterly_cashflow,
        }
    except Exception:
        return {}


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_analyst_recommendations(ticker: str) -> pd.DataFrame:
    try:
        t = yf.Ticker(ticker)
        recs = t.recommendations
        if recs is not None and not recs.empty:
            return recs.tail(10)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
