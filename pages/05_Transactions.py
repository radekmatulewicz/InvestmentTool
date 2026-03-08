import streamlit as st
import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.portfolio_service import (
    get_all_portfolios, get_transactions, add_transaction, delete_transaction
)
from utils.validators import validate_ticker, validate_quantity, validate_price, validate_fees
from components.data_tables import render_transactions_table

st.set_page_config(page_title="Transactions", page_icon="💳", layout="wide")
st.title("💳 Transactions")

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
        st.error("No portfolios found. Please restart the app.")
        st.stop()

st.markdown(f"**Portfolio:** {portfolio_name}")

# Add transaction form
with st.expander("Add Transaction", expanded=True):
    with st.form("add_transaction_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            ticker_input = st.text_input("Ticker Symbol", placeholder="e.g. AAPL").upper().strip()
            tx_type = st.selectbox("Type", ["buy", "sell"])
        with col2:
            qty_input = st.number_input("Quantity", min_value=0.0001, value=1.0, format="%.4f")
            price_input = st.number_input("Price per Unit ($)", min_value=0.0001, value=100.0, format="%.4f")
        with col3:
            fees_input = st.number_input("Fees ($)", min_value=0.0, value=0.0, format="%.4f")
            tx_date = st.date_input("Transaction Date", value=date.today())

        notes_input = st.text_input("Notes (optional)", placeholder="e.g. Bought on dip")
        submitted = st.form_submit_button("Add Transaction", type="primary", use_container_width=True)

        if submitted:
            errors = []

            valid_ticker, ticker_err = validate_ticker(ticker_input)
            if not valid_ticker:
                errors.append(f"Ticker: {ticker_err}")

            valid_qty, qty_err = validate_quantity(qty_input)
            if not valid_qty:
                errors.append(f"Quantity: {qty_err}")

            valid_price, price_err = validate_price(price_input)
            if not valid_price:
                errors.append(f"Price: {price_err}")

            valid_fees, fees_err = validate_fees(fees_input)
            if not valid_fees:
                errors.append(f"Fees: {fees_err}")

            if errors:
                for err in errors:
                    st.error(err)
            else:
                try:
                    add_transaction(
                        portfolio_id=portfolio_id,
                        ticker=ticker_input,
                        transaction_type=tx_type,
                        quantity=qty_input,
                        price_per_unit=price_input,
                        transaction_date=tx_date,
                        fees=fees_input,
                        notes=notes_input,
                    )
                    st.success(f"Added {tx_type.upper()} {qty_input:.4f} {ticker_input} @ ${price_input:.2f}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding transaction: {e}")

# Transactions table
st.markdown("---")
st.subheader("Transaction History")

transactions = get_transactions(portfolio_id)

if not transactions.empty:
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        filter_ticker = st.text_input("Filter by ticker", placeholder="e.g. AAPL").upper().strip()
    with col2:
        filter_type = st.selectbox("Filter by type", ["All", "buy", "sell"])

    if filter_ticker:
        transactions = transactions[transactions["ticker"].str.contains(filter_ticker, case=False)]
    if filter_type != "All":
        transactions = transactions[transactions["type"] == filter_type]

    render_transactions_table(transactions)

    # Delete section
    st.markdown("---")
    st.subheader("Delete Transaction")
    del_id = st.number_input("Transaction ID to delete", min_value=1, step=1)
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Delete", type="secondary"):
            if st.session_state.get("confirm_delete") == del_id:
                success = delete_transaction(int(del_id))
                if success:
                    st.success(f"Transaction {del_id} deleted.")
                    st.session_state.confirm_delete = None
                    st.rerun()
                else:
                    st.error(f"Transaction {del_id} not found.")
            else:
                st.session_state.confirm_delete = del_id
                st.warning(f"Click Delete again to confirm deletion of transaction #{del_id}")
else:
    st.info("No transactions yet. Use the form above to add your first transaction.")
