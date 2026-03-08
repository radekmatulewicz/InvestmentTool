import pandas as pd
import numpy as np
from decimal import Decimal
from database.connection import get_session
from database.models import Portfolio, Instrument, Transaction
from services.market_data import get_current_price, get_ticker_info, get_ticker_name


def get_all_portfolios() -> list[Portfolio]:
    session = get_session()
    try:
        return session.query(Portfolio).all()
    finally:
        session.close()


def get_portfolio_by_name(name: str) -> Portfolio | None:
    session = get_session()
    try:
        return session.query(Portfolio).filter_by(name=name).first()
    finally:
        session.close()


def get_or_create_instrument(ticker: str) -> Instrument:
    ticker = ticker.upper().strip()
    session = get_session()
    try:
        instrument = session.query(Instrument).filter_by(ticker=ticker).first()
        if not instrument:
            info = get_ticker_info(ticker)
            name = info.get("longName") or info.get("shortName") or ticker
            asset_type = _detect_asset_type(info)
            currency = info.get("currency", "USD")
            instrument = Instrument(
                ticker=ticker,
                name=name,
                asset_type=asset_type,
                currency=currency,
            )
            session.add(instrument)
            session.commit()
            session.refresh(instrument)
        inst_id = instrument.id
        return session.query(Instrument).get(inst_id)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _detect_asset_type(info: dict) -> str:
    qt = info.get("quoteType", "").lower()
    if qt == "etf":
        return "etf"
    if qt == "cryptocurrency":
        return "crypto"
    return "stock"


def add_transaction(
    portfolio_id: int,
    ticker: str,
    transaction_type: str,
    quantity: float,
    price_per_unit: float,
    transaction_date,
    fees: float = 0.0,
    notes: str = "",
) -> Transaction:
    instrument = get_or_create_instrument(ticker)
    session = get_session()
    try:
        tx = Transaction(
            portfolio_id=portfolio_id,
            instrument_id=instrument.id,
            transaction_type=transaction_type.lower(),
            quantity=Decimal(str(quantity)),
            price_per_unit=Decimal(str(price_per_unit)),
            fees=Decimal(str(fees)),
            transaction_date=transaction_date,
            notes=notes,
        )
        session.add(tx)
        session.commit()
        return tx
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_transaction(transaction_id: int) -> bool:
    session = get_session()
    try:
        tx = session.query(Transaction).get(transaction_id)
        if tx:
            session.delete(tx)
            session.commit()
            return True
        return False
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()


def get_transactions(portfolio_id: int) -> pd.DataFrame:
    session = get_session()
    try:
        txs = (
            session.query(Transaction, Instrument)
            .join(Instrument)
            .filter(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.transaction_date.desc())
            .all()
        )
        if not txs:
            return pd.DataFrame()

        rows = []
        for tx, inst in txs:
            rows.append({
                "id": tx.id,
                "ticker": inst.ticker,
                "name": inst.name,
                "type": tx.transaction_type,
                "quantity": float(tx.quantity),
                "price": float(tx.price_per_unit),
                "fees": float(tx.fees),
                "date": tx.transaction_date,
                "notes": tx.notes or "",
            })
        return pd.DataFrame(rows)
    finally:
        session.close()


def get_holdings(portfolio_id: int) -> pd.DataFrame:
    session = get_session()
    try:
        txs = (
            session.query(Transaction, Instrument)
            .join(Instrument)
            .filter(Transaction.portfolio_id == portfolio_id)
            .all()
        )
        if not txs:
            return pd.DataFrame()

        holdings = {}
        for tx, inst in txs:
            ticker = inst.ticker
            if ticker not in holdings:
                holdings[ticker] = {
                    "name": inst.name,
                    "ticker": ticker,
                    "buy_qty": 0.0,
                    "sell_qty": 0.0,
                    "buy_cost": 0.0,
                }
            qty = float(tx.quantity)
            price = float(tx.price_per_unit)
            fees = float(tx.fees)
            if tx.transaction_type == "buy":
                holdings[ticker]["buy_qty"] += qty
                holdings[ticker]["buy_cost"] += qty * price + fees
            elif tx.transaction_type == "sell":
                holdings[ticker]["sell_qty"] += qty

        rows = []
        for ticker, h in holdings.items():
            qty_held = h["buy_qty"] - h["sell_qty"]
            if qty_held <= 1e-8:
                continue
            avg_cost = h["buy_cost"] / h["buy_qty"] if h["buy_qty"] > 0 else 0
            current_price = get_current_price(ticker) or 0
            current_value = qty_held * current_price
            cost_basis = qty_held * avg_cost
            unrealized_pnl = current_value - cost_basis
            pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
            rows.append({
                "ticker": ticker,
                "name": h["name"],
                "quantity": qty_held,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "current_value": current_value,
                "cost_basis": cost_basis,
                "unrealized_pnl": unrealized_pnl,
                "pnl_pct": pnl_pct,
            })

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        total_value = df["current_value"].sum()
        df["weight_pct"] = (df["current_value"] / total_value * 100) if total_value > 0 else 0
        return df.sort_values("current_value", ascending=False).reset_index(drop=True)
    finally:
        session.close()


def get_portfolio_summary(portfolio_id: int) -> dict:
    holdings = get_holdings(portfolio_id)
    if holdings.empty:
        return {
            "total_value": 0,
            "total_cost": 0,
            "unrealized_pnl": 0,
            "unrealized_pnl_pct": 0,
            "num_positions": 0,
        }
    total_value = holdings["current_value"].sum()
    total_cost = holdings["cost_basis"].sum()
    unrealized_pnl = total_value - total_cost
    pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0
    return {
        "total_value": total_value,
        "total_cost": total_cost,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": pnl_pct,
        "num_positions": len(holdings),
    }
