import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0F172A",
    plot_bgcolor="#0F172A",
    font=dict(color="#F1F5F9"),
    margin=dict(l=40, r=20, t=40, b=40),
)


def candlestick_chart(
    df: pd.DataFrame,
    ticker: str,
    show_sma20: bool = True,
    show_sma50: bool = True,
    show_ema20: bool = False,
    show_bb: bool = True,
) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{ticker} Price", "RSI", "MACD"),
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price", increasing_line_color="#22c55e",
        decreasing_line_color="#ef4444",
    ), row=1, col=1)

    if show_sma20 and "SMA20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA20",
                                  line=dict(color="#3b82f6", width=1.5)), row=1, col=1)

    if show_sma50 and "SMA50" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA50",
                                  line=dict(color="#f59e0b", width=1.5)), row=1, col=1)

    if show_ema20 and "EMA20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA20",
                                  line=dict(color="#a855f7", width=1.5, dash="dash")), row=1, col=1)

    if show_bb and "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"], name="BB Upper",
                                  line=dict(color="#94a3b8", width=1, dash="dot"),
                                  showlegend=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_lower"], name="BB Lower",
                                  line=dict(color="#94a3b8", width=1, dash="dot"),
                                  fill="tonexty", fillcolor="rgba(148,163,184,0.05)",
                                  showlegend=True), row=1, col=1)

    # RSI
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                                  line=dict(color="#8b5cf6", width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", row=2, col=1)

    # MACD
    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
                                  line=dict(color="#06b6d4", width=1.5)), row=3, col=1)
        if "MACD_signal" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal",
                                      line=dict(color="#f97316", width=1.5)), row=3, col=1)
        if "MACD_hist" in df.columns:
            colors = ["#22c55e" if v >= 0 else "#ef4444" for v in df["MACD_hist"].fillna(0)]
            fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="Histogram",
                                  marker_color=colors), row=3, col=1)

    fig.update_layout(**DARK_LAYOUT, height=700, title=f"{ticker} Technical Analysis",
                      xaxis_rangeslider_visible=False)
    return fig


def allocation_pie_chart(holdings: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=holdings["ticker"],
        values=holdings["current_value"],
        hole=0.4,
        textinfo="label+percent",
        hovertemplate="%{label}<br>$%{value:,.2f}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(**DARK_LAYOUT, title="Portfolio Allocation", height=400)
    return fig


def portfolio_value_chart(values: pd.Series, title: str = "Portfolio Value Over Time") -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=values.index, y=values.values,
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.15)",
        line=dict(color="#2563EB", width=2),
        name="Portfolio Value",
        hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(**DARK_LAYOUT, title=title, height=400,
                      yaxis_title="Value ($)", xaxis_title="Date")
    return fig


def benchmark_comparison_chart(portfolio: pd.Series, benchmark: pd.Series, bench_name: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=portfolio.index, y=portfolio.values,
                              name="Portfolio", line=dict(color="#2563EB", width=2)))
    fig.add_trace(go.Scatter(x=benchmark.index, y=benchmark.values,
                              name=bench_name, line=dict(color="#f59e0b", width=2)))
    fig.update_layout(**DARK_LAYOUT, title="Portfolio vs Benchmark (Normalized to 100)",
                      height=400, yaxis_title="Value (Base=100)", xaxis_title="Date")
    return fig


def drawdown_chart(drawdown: pd.Series) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=drawdown.index, y=drawdown.values,
        fill="tozeroy",
        fillcolor="rgba(239,68,68,0.3)",
        line=dict(color="#ef4444", width=1),
        name="Drawdown",
        hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(**DARK_LAYOUT, title="Portfolio Drawdown", height=300,
                      yaxis_title="Drawdown (%)", xaxis_title="Date")
    return fig


def rolling_returns_chart(portfolio_returns: pd.Series, benchmark_returns: pd.Series,
                           bench_name: str, window: int = 30) -> go.Figure:
    p_roll = portfolio_returns.rolling(window).mean() * 252 * 100
    b_roll = benchmark_returns.rolling(window).mean() * 252 * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=p_roll.index, y=p_roll.values,
                              name="Portfolio", line=dict(color="#2563EB")))
    fig.add_trace(go.Scatter(x=b_roll.index, y=b_roll.values,
                              name=bench_name, line=dict(color="#f59e0b")))
    fig.add_hline(y=0, line_dash="dot", line_color="#94a3b8")
    fig.update_layout(**DARK_LAYOUT,
                      title=f"Rolling {window}-Day Annualized Returns",
                      height=300, yaxis_title="Annualized Return (%)")
    return fig
