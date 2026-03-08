import streamlit as st
import pandas as pd
from services.market_data import get_ticker_info, get_financials, get_analyst_recommendations


def get_valuation_metrics(ticker: str) -> dict:
    info = get_ticker_info(ticker)
    return {
        "P/E (Trailing)": info.get("trailingPE"),
        "P/E (Forward)": info.get("forwardPE"),
        "P/B Ratio": info.get("priceToBook"),
        "P/S Ratio": info.get("priceToSalesTrailing12Months"),
        "EV/EBITDA": info.get("enterpriseToEbitda"),
        "Market Cap": info.get("marketCap"),
    }


def get_quality_metrics(ticker: str) -> dict:
    info = get_ticker_info(ticker)
    return {
        "EPS (TTM)": info.get("trailingEps"),
        "ROE": info.get("returnOnEquity"),
        "Debt/Equity": info.get("debtToEquity"),
        "Current Ratio": info.get("currentRatio"),
        "Beta": info.get("beta"),
        "Revenue Growth": info.get("revenueGrowth"),
        "Earnings Growth": info.get("earningsGrowth"),
    }


def get_dividend_info(ticker: str) -> dict:
    info = get_ticker_info(ticker)
    div_rate = info.get("dividendRate")
    div_yield = info.get("dividendYield")
    if not div_rate and not div_yield:
        return {}
    return {
        "Dividend Rate": div_rate,
        "Dividend Yield": div_yield,
        "Payout Ratio": info.get("payoutRatio"),
        "Ex-Dividend Date": info.get("exDividendDate"),
    }


def get_fundamental_score(ticker: str) -> dict:
    info = get_ticker_info(ticker)
    scores = {}

    # Valuation score (lower P/E is better, scale 1-5)
    pe = info.get("trailingPE")
    if pe and pe > 0:
        if pe < 15:
            scores["Valuation"] = (5, "Undervalued")
        elif pe < 25:
            scores["Valuation"] = (4, "Fair Value")
        elif pe < 35:
            scores["Valuation"] = (3, "Fairly Valued")
        elif pe < 50:
            scores["Valuation"] = (2, "Overvalued")
        else:
            scores["Valuation"] = (1, "Highly Overvalued")

    # Profitability score
    roe = info.get("returnOnEquity")
    if roe is not None:
        if roe > 0.20:
            scores["Profitability"] = (5, "Excellent")
        elif roe > 0.15:
            scores["Profitability"] = (4, "Good")
        elif roe > 0.10:
            scores["Profitability"] = (3, "Average")
        elif roe > 0:
            scores["Profitability"] = (2, "Below Average")
        else:
            scores["Profitability"] = (1, "Poor")

    # Financial Health score
    de = info.get("debtToEquity")
    cr = info.get("currentRatio")
    if de is not None and cr is not None:
        health = 3
        if de < 50:
            health += 1
        elif de > 150:
            health -= 1
        if cr > 2:
            health += 1
        elif cr < 1:
            health -= 1
        health = max(1, min(5, health))
        label = {1: "Poor", 2: "Below Average", 3: "Average", 4: "Good", 5: "Excellent"}.get(health, "N/A")
        scores["Financial Health"] = (health, label)

    return scores
