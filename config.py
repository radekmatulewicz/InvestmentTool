import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "investment_tool.db")
DB_URL = f"sqlite:///{DB_PATH}"

BENCHMARKS = {
    "S&P 500 (SPY)": "SPY",
    "NASDAQ (QQQ)": "QQQ",
    "Dow Jones (DIA)": "DIA",
    "Russell 2000 (IWM)": "IWM",
    "Total Market (VTI)": "VTI",
}

DEFAULT_PORTFOLIO_NAME = "Main"

CACHE_TTL_SECONDS = 900  # 15 minutes

PERIODS = {
    "1W": "7d",
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "2Y": "2y",
    "5Y": "5y",
    "All": "max",
}

ASSET_TYPES = ["stock", "etf", "crypto", "other"]
