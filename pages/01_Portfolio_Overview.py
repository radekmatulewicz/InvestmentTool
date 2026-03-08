import streamlit as st
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.portfolio_service import get_holdings, get_portfolio_summary, get_all_portfolios, get_transactions
from services.benchmark_service import get_portfolio_daily_values, compute_performance_stats
from components.metrics_cards import render_portfolio_summary_cards
from components.data_tables import render_holdings_table
from components.charts import allocation_pie_chart, portfolio_value_chart
from utils.formatting import fmt_currency, fmt_pct, fmt_number

st.set_page_config(page_title="Portfolio Overview", page_icon="💼", layout="wide")
st.title("💼 Portfolio Overview")

portfolio_id = st.session_state.get("selected_portfolio_id")
portfolio_name = st.session_state.get("selected_portfolio_name", "Main")

if not portfolio_id:
    portfolios = get_all_portfolios()
    if portfolios:
        portfolio_id = portfolios[0].id
        portfolio_name = portfolios[0].name
        st.session_state.selected_portfolio_id = portfolio_id
        st.session_state.selected_portfolio_name = portfolio_name
    else:
        st.error("No portfolios found.")
        st.stop()

st.markdown(f"**Portfolio:** {portfolio_name}")

# ── Summary metrics ───────────────────────────────────────────────────────────
with st.spinner("Loading portfolio data..."):
    summary = get_portfolio_summary(portfolio_id)
    render_portfolio_summary_cards(summary)

st.markdown("---")

# ── Holdings table ────────────────────────────────────────────────────────────
st.subheader("Holdings")
holdings = get_holdings(portfolio_id)
render_holdings_table(holdings)

# ── Charts ────────────────────────────────────────────────────────────────────
if not holdings.empty:
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Allocation")
        fig = allocation_pie_chart(holdings)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        # Quick stats in right column
        if summary["total_cost"] > 0:
            cost_val = summary["total_cost"]
            curr_val = summary["total_value"]
            pnl = summary["unrealized_pnl"]
            st.markdown(f"**Cost basis:** {fmt_currency(cost_val)}")
            st.markdown(f"**Current value:** {fmt_currency(curr_val)}")
            color = "#22c55e" if pnl >= 0 else "#ef4444"
            st.markdown(
                f"**Unrealized P&L:** <span style='color:{color}'>"
                f"{fmt_currency(pnl)} ({fmt_pct(summary['unrealized_pnl_pct'])})</span>",
                unsafe_allow_html=True,
            )

st.markdown("---")

# ── Portfolio Value Over Time ─────────────────────────────────────────────────
st.subheader("Portfolio Value Over Time")

PERIODS = {
    "1 Month": 30,
    "3 Months": 90,
    "6 Months": 180,
    "1 Year": 365,
    "2 Years": 730,
    "All Time": None,
}

period_label = st.radio(
    "Period",
    list(PERIODS.keys()),
    index=5,
    horizontal=True,
    label_visibility="collapsed",
)

with st.spinner("Loading historical data..."):
    portfolio_values = get_portfolio_daily_values(portfolio_id)
    transactions = get_transactions(portfolio_id)

if portfolio_values.empty:
    st.info("Not enough historical data to plot portfolio value. Add transactions to get started.")
else:
    # Filter by selected period
    days = PERIODS[period_label]
    if days is not None:
        cutoff = pd.Timestamp.today() - pd.Timedelta(days=days)
        filtered_values = portfolio_values[portfolio_values.index >= cutoff]
    else:
        filtered_values = portfolio_values

    if filtered_values.empty:
        filtered_values = portfolio_values

    # Filter transactions to period
    filtered_txs = None
    if transactions is not None and not transactions.empty:
        tx_copy = transactions.copy()
        tx_copy["date"] = pd.to_datetime(tx_copy["date"])
        if days is not None:
            cutoff = pd.Timestamp.today() - pd.Timedelta(days=days)
            filtered_txs = tx_copy[tx_copy["date"] >= cutoff]
        else:
            filtered_txs = tx_copy

    fig = portfolio_value_chart(
        filtered_values,
        title=f"Portfolio Value — {period_label}",
        transactions=filtered_txs,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Performance stats ─────────────────────────────────────────────────────
    stats = compute_performance_stats(filtered_values)
    if stats:
        st.markdown("#### Performance Statistics")
        c1, c2, c3, c4, c5 = st.columns(5)
        total_ret = stats.get("Total Return (%)", 0)
        ann_ret = stats.get("Annualized Return (%)", 0)
        vol = stats.get("Volatility (%)", 0)
        sharpe = stats.get("Sharpe Ratio", 0)
        drawdown = stats.get("Max Drawdown (%)", 0)

        c1.metric("Total Return", fmt_pct(total_ret),
                  delta=fmt_pct(total_ret), delta_color="normal")
        c2.metric("Ann. Return", fmt_pct(ann_ret),
                  delta=fmt_pct(ann_ret), delta_color="normal")
        c3.metric("Volatility", fmt_pct(vol))
        c4.metric("Sharpe Ratio", fmt_number(sharpe))
        c5.metric("Max Drawdown", fmt_pct(drawdown))
