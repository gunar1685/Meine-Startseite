import json, math
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf

SYMBOLS = {
    "^GDAXI": "DAX",
    "^GSPC": "S&P 500",
    "^NDX": "NASDAQ 100",
    "^STOXX50E": "EURO STOXX 50",
}

def scalar(x):
    if hasattr(x, "iloc"):
        x = x.iloc[0]
    return float(x)

def close_series(symbol):
    df = yf.download(symbol, period="15mo", interval="1d", auto_adjust=False,
                     progress=False, threads=False)
    if df.empty:
        raise RuntimeError("Keine Kursdaten")
    close = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.astype(float)

def at_or_before(s, target):
    part = s[s.index <= pd.Timestamp(target)]
    return float(part.iloc[-1]) if len(part) else math.nan

def ret(latest, base):
    return (latest / base - 1) * 100 if math.isfinite(base) and base != 0 else math.nan

def metrics(s):
    latest = float(s.iloc[-1])
    d = s.index[-1]
    prev = float(s.iloc[-2]) if len(s) > 1 else math.nan
    return {
        "latest": latest,
        "date": d.strftime("%Y-%m-%d"),
        "d1": ret(latest, prev),
        "w1": ret(latest, at_or_before(s, d - pd.Timedelta(days=7))),
        "m1": ret(latest, at_or_before(s, d - pd.DateOffset(months=1))),
        "m6": ret(latest, at_or_before(s, d - pd.DateOffset(months=6))),
        "m12": ret(latest, at_or_before(s, d - pd.DateOffset(months=12))),
        "ytd": ret(latest, at_or_before(s, pd.Timestamp(d.year - 1, 12, 31))),
    }

out = {"updated": datetime.now(timezone.utc).isoformat(), "markets": {}}
for symbol, name in SYMBOLS.items():
    try:
        out["markets"][symbol] = {"name": name, "metrics": metrics(close_series(symbol)), "error": ""}
    except Exception as e:
        out["markets"][symbol] = {"name": name, "metrics": None, "error": str(e)}

Path("market-data.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
