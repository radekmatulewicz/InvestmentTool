import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.benchmark_service import get_portfolio_daily_values, compute_benchmark_comparison
from services.portfolio_service import get_all_portfolios
from components.charts import (
    benchmark_comparison_chart, drawdown_chart, rolling_returns_chart
)
from utils.formatting import fmt_pct, fmt_number
from config import BENCHMARKS

st.set_page_config(page_title="Market Comparison", page_icon="⚖️", layout="wide")
st.title("⚖️ Market Comparison")

portfolio_id = st.session_state.get("selected_portfolio_id")
portfolio_name = st.session_state.get("selected_portfolio_name", "Main")

if not portfolio_id:
    portfolios = get_all_portfolios()
    if portfolios:
        portfolio_id = portfolios[0].id
        portfolio_name = portfolios[0].name
    else:
        st.error("No portfolios found.")
        st.stop()

st.markdown(f"**Portfolio:** {portfolio_name}")

# Benchmark selection
col1, col2 = st.columns([2, 1])
with col1:
    benchmark_options = list(BENCHMARKS.keys()) + ["Custom"]
    selected_benchmark = st.selectbox("Benchmark", benchmark_options)
with col2:
    if selected_benchmark == "Custom":
        custom_ticker = st.text_input("Custom Ticker", placeholder="e.g. VGT").upper().strip()
        bench_ticker = custom_ticker or "SPY"
        bench_name = bench_ticker
    else:
        bench_ticker = BENCHMARKS[selected_benchmark]
        bench_name = selected_benchmark

if st.button("Compare", type="primary"):
    with st.spinner("Building portfolio history and fetching benchmark data..."):
        portfolio_values = get_portfolio_daily_values(portfolio_id)

        if portfolio_values.empty:
            st.warning("No portfolio data available. Add transactions first.")
            st.stop()

        result = compute_benchmark_comparison(portfolio_values, bench_ticker)

    if not result:
        st.error("Could not compute comparison. Check that the portfolio has data and the benchmark ticker is valid.")
        st.stop()

    # Normalized chart
    st.subheader("Performance Comparison (Base = 100)")
    fig = benchmark_comparison_chart(
        result["portfolio_norm"],
        result["benchmark_norm"],
        bench_name,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Stats table
    st.subheader("Performance Statistics")
    p_stats = result.get("portfolio_stats", {})
    b_stats = result.get("benchmark_stats", {})

    stats_rows = []
    all_metrics = set(list(p_stats.keys()) + list(b_stats.keys()))
    for metric in ["Total Return (%)", "Annualized Return (%)", "Volatility (%)", "Sharpe Ratio", "Max Drawdown (%)"]:
        if metric in p_stats or metric in b_stats:
            stats_rows.append({
                "Metric": metric,
                "Portfolio": p_stats.get(metric, "N/A"),
                bench_name: b_stats.get(metric, "N/A"),
            })

    if result.get("beta") is not None:
        stats_rows.append({"Metric": "Beta", "Portfolio": fmt_number(result["beta"]), bench_name: "1.00"})
    if result.get("alpha") is not None:
        stats_rows.append({"Metric": "Alpha (Annualized %)", "Portfolio": fmt_number(result["alpha"]), bench_name: "0.00"})
    if result.get("correlation") is not None:
        stats_rows.append({"Metric": "Correlation", "Portfolio": fmt_number(result["correlation"]), bench_name: "1.00"})

    import pandas as pd
    stats_df = pd.DataFrame(stats_rows)
    if not stats_df.empty:
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

    # Rolling returns
    if not result["portfolio_returns"].empty and not result["benchmark_returns"].empty:
        st.subheader("Rolling 30-Day Returns")
        fig = rolling_returns_chart(result["portfolio_returns"], result["benchmark_returns"], bench_name)
        st.plotly_chart(fig, use_container_width=True)

    # Drawdown
    if not result["drawdown"].empty:
        st.subheader("Portfolio Drawdown")
        fig = drawdown_chart(result["drawdown"])
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select a benchmark above and click Compare.")
