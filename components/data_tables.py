import streamlit as st
import pandas as pd
from utils.formatting import fmt_currency, fmt_pct, fmt_number


def render_holdings_table(holdings: pd.DataFrame):
    if holdings.empty:
        st.info("No holdings found. Add transactions to get started.")
        return

    display = holdings.copy()
    display["Quantity"] = display["quantity"].apply(lambda x: fmt_number(x, 4))
    display["Avg Cost"] = display["avg_cost"].apply(fmt_currency)
    display["Current Price"] = display["current_price"].apply(fmt_currency)
    display["Current Value"] = display["current_value"].apply(fmt_currency)
    display["P&L $"] = display["unrealized_pnl"].apply(fmt_currency)
    display["P&L %"] = display["pnl_pct"].apply(fmt_pct)
    display["Weight %"] = display["weight_pct"].apply(lambda x: fmt_pct(x, 1))

    cols_to_show = ["ticker", "name", "Quantity", "Avg Cost", "Current Price",
                    "Current Value", "P&L $", "P&L %", "Weight %"]
    display = display[cols_to_show].rename(columns={"ticker": "Ticker", "name": "Name"})

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )


def render_transactions_table(transactions: pd.DataFrame) -> int | None:
    if transactions.empty:
        st.info("No transactions yet.")
        return None

    display = transactions.copy()
    display["Price"] = display["price"].apply(fmt_currency)
    display["Fees"] = display["fees"].apply(lambda x: fmt_currency(x, decimals=4))
    display["Quantity"] = display["quantity"].apply(lambda x: fmt_number(x, 4))
    display["Date"] = pd.to_datetime(display["date"]).dt.strftime("%Y-%m-%d")

    cols = ["id", "ticker", "name", "type", "Quantity", "Price", "Fees", "Date", "notes"]
    available = [c for c in cols if c in display.columns]
    display = display[available].rename(columns={
        "id": "ID", "ticker": "Ticker", "name": "Name", "type": "Type",
        "notes": "Notes"
    })

    st.dataframe(display, use_container_width=True, hide_index=True)
    return None


def render_financial_statement(df: pd.DataFrame, title: str):
    if df is None or df.empty:
        st.warning(f"No {title} data available.")
        return
    st.subheader(title)
    df_display = df.copy()
    df_display.columns = [str(c)[:10] if hasattr(c, '__str__') else c for c in df_display.columns]
    st.dataframe(df_display, use_container_width=True)
