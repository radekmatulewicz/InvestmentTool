import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.fundamental_analysis import (
    get_valuation_metrics, get_quality_metrics,
    get_dividend_info, get_fundamental_score
)
from services.market_data import get_financials, get_analyst_recommendations, get_ticker_info
from components.data_tables import render_financial_statement
from utils.formatting import fmt_currency, fmt_pct, fmt_number
from utils.validators import validate_ticker

st.set_page_config(page_title="Fundamental Analysis", page_icon="🔬", layout="wide")
st.title("🔬 Fundamental Analysis")

col1, col2 = st.columns([3, 1])
with col1:
    ticker_input = st.text_input("Ticker Symbol", value="AAPL", placeholder="e.g. AAPL").upper().strip()
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

if ticker_input and (analyze_btn or "fund_analyzed" in st.session_state):
    if analyze_btn:
        st.session_state.fund_analyzed = ticker_input

    ticker = st.session_state.get("fund_analyzed", ticker_input)
    valid, err = validate_ticker(ticker)
    if not valid:
        st.error(f"Invalid ticker: {err}")
        st.stop()

    with st.spinner(f"Loading fundamental data for {ticker}..."):
        info = get_ticker_info(ticker)
        valuation = get_valuation_metrics(ticker)
        quality = get_quality_metrics(ticker)
        dividend = get_dividend_info(ticker)
        scores = get_fundamental_score(ticker)
        financials = get_financials(ticker)
        recommendations = get_analyst_recommendations(ticker)

    name = info.get("longName") or info.get("shortName") or ticker
    st.markdown(f"## {name} ({ticker})")
    st.caption(f"{info.get('sector', '')} | {info.get('industry', '')}")

    # Scores
    if scores:
        st.markdown("### Fundamental Scores")
        score_cols = st.columns(len(scores))
        score_colors = {5: "#16a34a", 4: "#22c55e", 3: "#d97706", 2: "#ef4444", 1: "#991b1b"}
        for i, (category, (score, label)) in enumerate(scores.items()):
            color = score_colors.get(score, "#6b7280")
            with score_cols[i]:
                st.markdown(
                    f"""<div style='background:{color};border-radius:8px;padding:12px;text-align:center;'>
                    <div style='font-size:0.9em;'>{category}</div>
                    <div style='font-size:2em;font-weight:bold;'>{score}/5</div>
                    <div>{label}</div></div>""",
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # Metrics
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Valuation Metrics")
        for metric, value in valuation.items():
            if value is not None:
                if metric == "Market Cap":
                    formatted = fmt_currency(value)
                elif isinstance(value, float) and value < 100:
                    formatted = fmt_number(value)
                else:
                    formatted = fmt_number(value)
                st.markdown(f"**{metric}:** {formatted}")

    with col2:
        st.subheader("Quality Metrics")
        for metric, value in quality.items():
            if value is not None:
                if metric in ["ROE", "Revenue Growth", "Earnings Growth"]:
                    formatted = fmt_pct(value * 100)
                elif metric == "Debt/Equity":
                    formatted = fmt_number(value)
                else:
                    formatted = fmt_number(value)
                st.markdown(f"**{metric}:** {formatted}")

    # Dividend section
    if dividend:
        st.markdown("---")
        st.subheader("Dividend Information")
        div_cols = st.columns(len(dividend))
        for i, (key, value) in enumerate(dividend.items()):
            with div_cols[i]:
                if key == "Dividend Yield" and value:
                    st.metric(key, fmt_pct(value * 100))
                elif key == "Dividend Rate" and value:
                    st.metric(key, fmt_currency(value))
                elif key == "Payout Ratio" and value:
                    st.metric(key, fmt_pct(value * 100))
                else:
                    st.metric(key, str(value) if value else "N/A")

    st.markdown("---")

    # Financial statements
    st.subheader("Financial Statements")
    tab_annual, tab_quarterly = st.tabs(["Annual", "Quarterly"])

    with tab_annual:
        tab_inc, tab_bs, tab_cf = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
        with tab_inc:
            render_financial_statement(financials.get("income_stmt_annual"), "Income Statement")
        with tab_bs:
            render_financial_statement(financials.get("balance_sheet_annual"), "Balance Sheet")
        with tab_cf:
            render_financial_statement(financials.get("cash_flow_annual"), "Cash Flow")

    with tab_quarterly:
        tab_inc, tab_bs, tab_cf = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
        with tab_inc:
            render_financial_statement(financials.get("income_stmt_quarterly"), "Income Statement (Q)")
        with tab_bs:
            render_financial_statement(financials.get("balance_sheet_quarterly"), "Balance Sheet (Q)")
        with tab_cf:
            render_financial_statement(financials.get("cash_flow_quarterly"), "Cash Flow (Q)")

    # Analyst recommendations
    if not recommendations.empty:
        st.markdown("---")
        st.subheader("Analyst Recommendations")
        st.dataframe(recommendations, use_container_width=True, hide_index=True)
else:
    st.info("Enter a ticker symbol above and click Analyze.")
