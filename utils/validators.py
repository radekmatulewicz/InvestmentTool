import re
from services.market_data import validate_ticker as _validate_ticker


def is_valid_ticker_format(ticker: str) -> bool:
    if not ticker:
        return False
    ticker = ticker.strip().upper()
    pattern = r"^[A-Z0-9.\-\^=]{1,20}$"
    return bool(re.match(pattern, ticker))


def validate_ticker(ticker: str) -> tuple[bool, str]:
    ticker = ticker.strip().upper()
    if not is_valid_ticker_format(ticker):
        return False, "Invalid ticker format"
    try:
        valid = _validate_ticker(ticker)
        if valid:
            return True, ""
        return False, f"Ticker '{ticker}' not found or has no price data"
    except Exception as e:
        return False, str(e)


def validate_quantity(qty) -> tuple[bool, str]:
    try:
        qty = float(qty)
        if qty <= 0:
            return False, "Quantity must be greater than 0"
        return True, ""
    except Exception:
        return False, "Quantity must be a number"


def validate_price(price) -> tuple[bool, str]:
    try:
        price = float(price)
        if price <= 0:
            return False, "Price must be greater than 0"
        return True, ""
    except Exception:
        return False, "Price must be a number"


def validate_fees(fees) -> tuple[bool, str]:
    try:
        fees = float(fees)
        if fees < 0:
            return False, "Fees cannot be negative"
        return True, ""
    except Exception:
        return False, "Fees must be a number"
