def fmt_currency(value, currency="$", decimals=2) -> str:
    if value is None:
        return "N/A"
    try:
        value = float(value)
        if abs(value) >= 1e12:
            return f"{currency}{value/1e12:.2f}T"
        if abs(value) >= 1e9:
            return f"{currency}{value/1e9:.2f}B"
        if abs(value) >= 1e6:
            return f"{currency}{value/1e6:.2f}M"
        return f"{currency}{value:,.{decimals}f}"
    except Exception:
        return "N/A"


def fmt_pct(value, decimals=2) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{decimals}f}%"
    except Exception:
        return "N/A"


def fmt_number(value, decimals=2) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return "N/A"


def pnl_color(value) -> str:
    try:
        return "green" if float(value) >= 0 else "red"
    except Exception:
        return "gray"


def fmt_metric_value(value, metric_type="currency") -> str:
    if metric_type == "currency":
        return fmt_currency(value)
    elif metric_type == "pct":
        return fmt_pct(value)
    elif metric_type == "number":
        return fmt_number(value)
    return str(value) if value is not None else "N/A"
