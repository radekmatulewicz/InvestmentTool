import streamlit as st
from utils.formatting import fmt_currency, fmt_pct, fmt_number


def render_portfolio_summary_cards(summary: dict):
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Value", fmt_currency(summary.get("total_value", 0)))
    with col2:
        st.metric("Total Cost", fmt_currency(summary.get("total_cost", 0)))
    with col3:
        pnl = summary.get("unrealized_pnl", 0)
        pnl_pct = summary.get("unrealized_pnl_pct", 0)
        delta_str = fmt_pct(pnl_pct)
        st.metric("Unrealized P&L", fmt_currency(pnl), delta=delta_str)
    with col4:
        st.metric("# Positions", summary.get("num_positions", 0))
    with col5:
        st.metric("Return %", fmt_pct(summary.get("unrealized_pnl_pct", 0)))


def render_signal_badges(signals: dict):
    colors = {"BUY": "#16a34a", "SELL": "#dc2626", "HOLD": "#d97706"}
    cols = st.columns(len(signals))
    for i, (name, (signal, detail)) in enumerate(signals.items()):
        color = colors.get(signal, "#6b7280")
        with cols[i]:
            st.markdown(
                f"""<div style='background:{color};border-radius:8px;padding:8px 12px;text-align:center;'>
                <b>{name}</b><br/><span style='font-size:1.1em;'>{signal}</span><br/>
                <small>{detail}</small></div>""",
                unsafe_allow_html=True,
            )


def render_stat_card(title: str, value: str, color: str = None):
    style = f"color:{color};" if color else ""
    st.markdown(
        f"""<div style='background:#1E293B;border-radius:8px;padding:12px 16px;margin:4px 0;'>
        <div style='font-size:0.85em;color:#94a3b8;'>{title}</div>
        <div style='font-size:1.3em;font-weight:bold;{style}'>{value}</div>
        </div>""",
        unsafe_allow_html=True,
    )
