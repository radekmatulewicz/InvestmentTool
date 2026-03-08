import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.market_data import get_historical_prices, get_ticker_info
from services.technical_analysis import compute_indicators, get_signals, get_support_resistance
from services.portfolio_service import get_all_portfolios, add_transaction
from components.charts import candlestick_chart
from components.metrics_cards import render_signal_badges
from utils.validators import validate_ticker
from utils.formatting import fmt_currency
from config import PERIODS
from datetime import date

st.set_page_config(page_title="Stock Analysis", page_icon="📊", layout="wide")
st.title("📊 Stock Analysis")

# Ticker input
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    ticker_input = st.text_input("Enter Ticker Symbol", value="AAPL", placeholder="e.g. AAPL, SPY, BTC-USD").upper().strip()
with col2:
    period_label = st.selectbox("Period", list(PERIODS.keys()), index=4)
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

if ticker_input and (analyze_btn or "last_analyzed" in st.session_state):
    if analyze_btn:
        st.session_state.last_analyzed = ticker_input
        st.session_state.last_period = period_label

    ticker = st.session_state.get("last_analyzed", ticker_input)
    period = PERIODS.get(st.session_state.get("last_period", period_label), "1y")

    valid, err = validate_ticker(ticker)
    if not valid:
        st.error(f"Invalid ticker: {err}")
        st.stop()

    with st.spinner(f"Loading data for {ticker}..."):
        df = get_historical_prices(ticker, period)
        info = get_ticker_info(ticker)

    if df.empty:
        st.error(f"No price data found for {ticker}")
        st.stop()

    # Ticker info header
    name = info.get("longName") or info.get("shortName") or ticker
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    price_change = info.get("regularMarketChange")
    price_change_pct = info.get("regularMarketChangePercent")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"### {name}")
        st.caption(f"{ticker} | {info.get('exchange', '')}")
    with col2:
        if current_price:
            st.metric("Price", fmt_currency(current_price),
                      delta=f"{price_change_pct:.2f}%" if price_change_pct else None)
    with col3:
        st.metric("52W High", fmt_currency(info.get("fiftyTwoWeekHigh")))
    with col4:
        st.metric("52W Low", fmt_currency(info.get("fiftyTwoWeekLow")))

    # Chart overlays
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        show_sma20 = st.checkbox("SMA 20", value=True)
    with col2:
        show_sma50 = st.checkbox("SMA 50", value=True)
    with col3:
        show_ema20 = st.checkbox("EMA 20", value=False)
    with col4:
        show_bb = st.checkbox("Bollinger Bands", value=True)

    # Compute indicators
    df_ind = compute_indicators(df)
    signals = get_signals(df_ind)
    sr = get_support_resistance(df_ind)

    # Signal badges
    if signals:
        st.markdown("#### Signals")
        render_signal_badges(signals)

    # Support/Resistance
    if sr:
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"Support: {fmt_currency(sr.get('support'))}")
        with col2:
            st.warning(f"Resistance: {fmt_currency(sr.get('resistance'))}")

    # Chart
    fig = candlestick_chart(df_ind, ticker, show_sma20, show_sma50, show_ema20, show_bb)
    st.plotly_chart(fig, use_container_width=True)

    # Add to portfolio form
    st.markdown("---")
    with st.expander("Add to Portfolio"):
        portfolios = get_all_portfolios()
        if portfolios:
            with st.form("add_from_analysis"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    portfolio_names = [p.name for p in portfolios]
                    sel_port = st.selectbox("Portfolio", portfolio_names)
                with col2:
                    tx_type = st.selectbox("Type", ["buy", "sell"])
                with col3:
                    qty = st.number_input("Quantity", min_value=0.0001, value=1.0, format="%.4f")
                with col4:
                    price = st.number_input("Price", min_value=0.0001,
                                             value=float(current_price) if current_price else 1.0,
                                             format="%.4f")
                tx_date = st.date_input("Date", value=date.today())
                fees = st.number_input("Fees ($)", min_value=0.0, value=0.0, format="%.4f")
                if st.form_submit_button("Add Transaction", type="primary"):
                    portfolio_id = next(p.id for p in portfolios if p.name == sel_port)
                    add_transaction(portfolio_id, ticker, tx_type, qty, price, tx_date, fees)
                    st.success(f"Added {tx_type.upper()} {qty:.4f} {ticker} @ ${price:.2f}")
        else:
            st.warning("No portfolios found.")
else:
    st.info("Enter a ticker symbol above and click Analyze.")
