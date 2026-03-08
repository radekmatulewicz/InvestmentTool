import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.migrations import init_db
from services.portfolio_service import get_all_portfolios
from config import DEFAULT_PORTFOLIO_NAME

st.set_page_config(
    page_title="Investment Analysis Tool",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
init_db()

# Session state defaults
if "selected_portfolio_id" not in st.session_state:
    st.session_state.selected_portfolio_id = None
if "selected_portfolio_name" not in st.session_state:
    st.session_state.selected_portfolio_name = DEFAULT_PORTFOLIO_NAME

# Sidebar
with st.sidebar:
    st.title("📈 Investment Tool")
    st.markdown("---")

    portfolios = get_all_portfolios()
    portfolio_names = [p.name for p in portfolios]

    if portfolio_names:
        default_idx = 0
        if st.session_state.selected_portfolio_name in portfolio_names:
            default_idx = portfolio_names.index(st.session_state.selected_portfolio_name)

        selected_name = st.selectbox(
            "Portfolio",
            portfolio_names,
            index=default_idx,
        )
        selected_portfolio = next((p for p in portfolios if p.name == selected_name), None)
        if selected_portfolio:
            st.session_state.selected_portfolio_id = selected_portfolio.id
            st.session_state.selected_portfolio_name = selected_portfolio.name

    st.markdown("---")
    st.markdown("### Navigation")
    st.page_link("pages/01_Portfolio_Overview.py", label="Portfolio Overview", icon="💼")
    st.page_link("pages/02_Stock_Analysis.py", label="Stock Analysis", icon="📊")
    st.page_link("pages/03_Fundamental_Analysis.py", label="Fundamental Analysis", icon="🔬")
    st.page_link("pages/04_Market_Comparison.py", label="Market Comparison", icon="⚖️")
    st.page_link("pages/05_Transactions.py", label="Transactions", icon="💳")
    st.markdown("---")
    st.caption("Data: Yahoo Finance | Updated every 15 min")

# Main page content
st.title("📈 Investment Analysis Tool")
st.markdown("""
Welcome to your personal investment analysis dashboard.

**Get started:**
1. Go to **Transactions** to add your holdings
2. View your portfolio in **Portfolio Overview**
3. Analyze stocks with **Stock Analysis**
4. Deep dive with **Fundamental Analysis**
5. Compare performance in **Market Comparison**
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("**Portfolio**: Select from the sidebar")
with col2:
    st.info("**Data**: Live prices via Yahoo Finance")
with col3:
    st.info("**Refresh**: Prices update every 15 min")
