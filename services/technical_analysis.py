import pandas as pd
import numpy as np
import ta


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 20:
        return df
    df = df.copy()

    # Moving averages
    df["SMA20"] = df["Close"].rolling(window=20).mean()
    df["SMA50"] = df["Close"].rolling(window=50).mean()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_mid"] = bb.bollinger_mavg()
    df["BB_lower"] = bb.bollinger_lband()

    # RSI
    rsi_indicator = ta.momentum.RSIIndicator(close=df["Close"], window=14)
    df["RSI"] = rsi_indicator.rsi()

    # MACD
    macd_indicator = ta.trend.MACD(close=df["Close"])
    df["MACD"] = macd_indicator.macd()
    df["MACD_signal"] = macd_indicator.macd_signal()
    df["MACD_hist"] = macd_indicator.macd_diff()

    return df


def get_signals(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    signals = {}
    last = df.iloc[-1]

    # RSI signal
    rsi = last.get("RSI")
    if pd.notna(rsi):
        if rsi < 30:
            signals["RSI"] = ("BUY", f"RSI={rsi:.1f} (oversold)")
        elif rsi > 70:
            signals["RSI"] = ("SELL", f"RSI={rsi:.1f} (overbought)")
        else:
            signals["RSI"] = ("HOLD", f"RSI={rsi:.1f} (neutral)")

    # MACD signal
    if len(df) >= 2:
        macd_now = last.get("MACD")
        macd_sig_now = last.get("MACD_signal")
        prev = df.iloc[-2]
        macd_prev = prev.get("MACD")
        macd_sig_prev = prev.get("MACD_signal")
        if all(pd.notna(x) for x in [macd_now, macd_sig_now, macd_prev, macd_sig_prev]):
            if macd_prev < macd_sig_prev and macd_now > macd_sig_now:
                signals["MACD"] = ("BUY", "MACD crossed above signal")
            elif macd_prev > macd_sig_prev and macd_now < macd_sig_now:
                signals["MACD"] = ("SELL", "MACD crossed below signal")
            else:
                above = macd_now > macd_sig_now
                signals["MACD"] = ("HOLD", f"MACD {'above' if above else 'below'} signal")

    # Bollinger Bands signal
    close = last.get("Close")
    bb_upper = last.get("BB_upper")
    bb_lower = last.get("BB_lower")
    if all(pd.notna(x) for x in [close, bb_upper, bb_lower]):
        band_range = bb_upper - bb_lower
        if band_range > 0:
            position = (close - bb_lower) / band_range
            if position >= 0.9:
                signals["BB"] = ("SELL", f"Price near upper band ({position:.0%})")
            elif position <= 0.1:
                signals["BB"] = ("BUY", f"Price near lower band ({position:.0%})")
            else:
                signals["BB"] = ("HOLD", f"Price mid-band ({position:.0%})")

    # Overall signal
    if signals:
        counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
        for sig, _ in signals.values():
            counts[sig] += 1
        overall = max(counts, key=counts.get)
        signals["Overall"] = (overall, f"B:{counts['BUY']} S:{counts['SELL']} H:{counts['HOLD']}")

    return signals


def get_support_resistance(df: pd.DataFrame, window: int = 20) -> dict:
    if df.empty or len(df) < window * 2:
        return {}
    recent = df.tail(window * 2)
    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())
    return {"support": support, "resistance": resistance}
