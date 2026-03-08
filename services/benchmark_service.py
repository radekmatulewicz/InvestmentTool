import pandas as pd
import numpy as np
from services.market_data import get_historical_prices_range
from database.connection import get_session
from database.models import Transaction, Instrument


def get_portfolio_daily_values(portfolio_id: int) -> pd.Series:
    session = get_session()
    try:
        txs = (
            session.query(Transaction, Instrument)
            .join(Instrument)
            .filter(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.transaction_date)
            .all()
        )
        if not txs:
            return pd.Series(dtype=float)

        start_date = min(tx.transaction_date for tx, _ in txs)
        end_date = pd.Timestamp.today().date()
        tickers = list({inst.ticker for _, inst in txs})

        price_data = {}
        for ticker in tickers:
            hist = get_historical_prices_range(
                ticker,
                start_date.isoformat(),
                end_date.isoformat(),
            )
            if not hist.empty:
                price_data[ticker] = hist["Close"]

        if not price_data:
            return pd.Series(dtype=float)

        # Build daily holdings
        date_range = pd.bdate_range(start=start_date, end=end_date)
        portfolio_values = pd.Series(0.0, index=date_range)

        tx_df = pd.DataFrame([
            {
                "date": pd.Timestamp(tx.transaction_date),
                "ticker": inst.ticker,
                "type": tx.transaction_type,
                "qty": float(tx.quantity),
                "price": float(tx.price_per_unit),
                "fees": float(tx.fees),
            }
            for tx, inst in txs
        ])

        holdings = {t: 0.0 for t in tickers}
        cash = 0.0

        for date in date_range:
            day_txs = tx_df[tx_df["date"].dt.date == date.date()]
            for _, row in day_txs.iterrows():
                if row["type"] == "buy":
                    holdings[row["ticker"]] += row["qty"]
                    cash -= row["qty"] * row["price"] + row["fees"]
                elif row["type"] == "sell":
                    holdings[row["ticker"]] -= row["qty"]
                    cash += row["qty"] * row["price"] - row["fees"]

            day_value = 0.0
            for ticker, qty in holdings.items():
                if ticker in price_data and qty > 0:
                    prices = price_data[ticker]
                    # Find the last available price on or before this date
                    available = prices[prices.index <= date]
                    if not available.empty:
                        day_value += qty * float(available.iloc[-1])

            portfolio_values[date] = day_value

        return portfolio_values[portfolio_values > 0]

    finally:
        session.close()


def compute_performance_stats(returns: pd.Series, risk_free_rate: float = 0.05) -> dict:
    if returns.empty or len(returns) < 2:
        return {}

    total_return = (returns.iloc[-1] / returns.iloc[0] - 1) * 100
    n_years = (returns.index[-1] - returns.index[0]).days / 365.25
    annualized_return = ((returns.iloc[-1] / returns.iloc[0]) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0

    daily_returns = returns.pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252) * 100

    excess_returns = daily_returns - risk_free_rate / 252
    sharpe = (excess_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0

    rolling_max = returns.cummax()
    drawdown = (returns - rolling_max) / rolling_max * 100
    max_drawdown = drawdown.min()

    return {
        "Total Return (%)": round(total_return, 2),
        "Annualized Return (%)": round(annualized_return, 2),
        "Volatility (%)": round(volatility, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Max Drawdown (%)": round(max_drawdown, 2),
    }


def compute_benchmark_comparison(portfolio_values: pd.Series, benchmark_ticker: str) -> dict:
    if portfolio_values.empty:
        return {}

    start = portfolio_values.index[0].date().isoformat()
    end = portfolio_values.index[-1].date().isoformat()

    bench_hist = get_historical_prices_range(benchmark_ticker, start, end)
    if bench_hist.empty:
        return {}

    bench_values = bench_hist["Close"].reindex(portfolio_values.index, method="ffill").dropna()

    # Normalize to 100
    portfolio_norm = portfolio_values / portfolio_values.iloc[0] * 100
    bench_norm = bench_values / bench_values.iloc[0] * 100

    # Align
    common_idx = portfolio_norm.index.intersection(bench_norm.index)
    if len(common_idx) < 2:
        return {}

    p = portfolio_norm[common_idx]
    b = bench_norm[common_idx]

    p_returns = p.pct_change().dropna()
    b_returns = b.pct_change().dropna()

    common_returns = p_returns.index.intersection(b_returns.index)
    p_ret = p_returns[common_returns]
    b_ret = b_returns[common_returns]

    # Beta and alpha
    if len(p_ret) > 1 and b_ret.std() > 0:
        beta = p_ret.cov(b_ret) / b_ret.var()
        alpha = p_ret.mean() - beta * b_ret.mean()
        alpha_annualized = alpha * 252 * 100
        correlation = p_ret.corr(b_ret)
    else:
        beta = None
        alpha_annualized = None
        correlation = None

    portfolio_stats = compute_performance_stats(portfolio_values[common_idx])
    bench_stats = compute_performance_stats(bench_values[common_idx])

    return {
        "portfolio_norm": p,
        "benchmark_norm": b,
        "portfolio_stats": portfolio_stats,
        "benchmark_stats": bench_stats,
        "beta": round(beta, 3) if beta is not None else None,
        "alpha": round(alpha_annualized, 2) if alpha_annualized is not None else None,
        "correlation": round(correlation, 3) if correlation is not None else None,
        "portfolio_returns": p_returns,
        "benchmark_returns": b_returns,
        "drawdown": (p - p.cummax()) / p.cummax() * 100,
    }
