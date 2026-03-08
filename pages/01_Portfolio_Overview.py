import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.portfolio_service import get_holdings, get_portfolio_summary, get_all_portfolios
from services.benchmark_service import get_portfolio_daily_values
from components.metrics_cards import render_portfolio_summary_cards
from components.data_tables import render_holdings_table
from components.charts import allocation_pie_chart, portfolio_value_chart

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

# Summary metrics
with st.spinner("Loading portfolio data..."):
    summary = get_portfolio_summary(portfolio_id)
    render_portfolio_summary_cards(summary)

st.markdown("---")

# Holdings table
st.subheader("Holdings")
holdings = get_holdings(portfolio_id)
render_holdings_table(holdings)

# Charts
if not holdings.empty:
    st.markdown("---")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Allocation")
        fig = allocation_pie_chart(holdings)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Portfolio Value Over Time")
        with st.spinner("Loading historical data..."):
            portfolio_values = get_portfolio_daily_values(portfolio_id)
        if not portfolio_values.empty:
            fig = portfolio_value_chart(portfolio_values)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough historical data to plot portfolio value.")
