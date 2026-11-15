"""Library of long-only strategies. Each returns the df with a 'position' column:
1 = be invested, 0 = be in cash, NaN = not enough history yet.
Signals are evaluated on the daily close; backtests act on the next bar.
"""
import numpy as np
import pandas as pd

from . import indicators as ind
from .strategy import BUY, SELL, StrategyConfig, analyze


def _hold(entry: pd.Series, exit_: pd.Series, ready: pd.Series) -> pd.Series:
    """Turn entry/exit conditions into a 0/1 position that stays until the opposite fires."""
    pos, out = 0, []
    for e, x, r in zip(entry.to_numpy(), exit_.to_numpy(), ready.to_numpy()):
        if not r:
            out.append(np.nan)
            continue
        if pos == 0 and e:
            pos = 1
        elif pos == 1 and x:
            pos = 0
        out.append(pos)
    return pd.Series(out, index=entry.index, dtype=float)


def buy_hold(df):
    out = df.copy()
    out["position"] = 1.0
    return out


def score(df):
    """Original 4-indicator score (trend, golden cross, MACD, RSI)."""
    out = analyze(df, StrategyConfig())
    out["position"] = _hold(out["action"] == BUY, out["action"] == SELL, out["action"].notna())
    return out


def sma_trend(df, n=200):
    """In when close is above the 200-day average, out when below."""
    out = df.copy()
    out["sma"] = ind.sma(out["Close"], n)
    above = out["Close"] > out["sma"]
    out["position"] = _hold(above, ~above, out["sma"].notna())
    return out


def sma_trend_buffer(df, n=200, band=0.03):
    """Like sma_trend, but only exit when price is 3% below the average (fewer whipsaws)."""
    out = df.copy()
    out["sma"] = ind.sma(out["Close"], n)
    out["position"] = _hold(
        out["Close"] > out["sma"], out["Close"] < out["sma"] * (1 - band), out["sma"].notna()
    )
    return out


def golden_cross(df, fast=50, slow=200):
    out = df.copy()
    out["sma_fast"], out["sma_slow"] = ind.sma(out["Close"], fast), ind.sma(out["Close"], slow)
    up = out["sma_fast"] > out["sma_slow"]
    out["position"] = _hold(up, ~up, out["sma_slow"].notna())
    return out


def momentum_12m(df, lookback=252):
    """Time-series momentum: in when price is higher than 12 months ago."""
    out = df.copy()
    out["mom"] = out["Close"] / out["Close"].shift(lookback) - 1
    up = out["mom"] > 0
    out["position"] = _hold(up, ~up, out["mom"].notna())
    return out


def donchian(df, entry=55, exit_=20):
    """Breakout: buy a new 55-day high, sell a new 20-day low."""
    out = df.copy()
    hi = out["Close"].rolling(entry).max().shift(1)
    lo = out["Close"].rolling(exit_).min().shift(1)
    out["position"] = _hold(out["Close"] > hi, out["Close"] < lo, hi.notna())
    return out


def rsi2_pullback(df, trend=200, low=10, exit_sma=5):
    """Buy short dips (RSI(2) < 10) only while in a long-term uptrend; sell on the bounce."""
    out = df.copy()
    out["sma"] = ind.sma(out["Close"], trend)
    out["rsi2"] = ind.rsi(out["Close"], 2)
    out["sma_exit"] = ind.sma(out["Close"], exit_sma)
    entry = (out["Close"] > out["sma"]) & (out["rsi2"] < low)
    exit_ = (out["Close"] > out["sma_exit"]) | (out["Close"] < out["sma"] * 0.95)
    out["position"] = _hold(entry, exit_, out["sma"].notna() & out["rsi2"].notna())
    return out


def trend_or_dip(df, n=200, band=0.03):
    """Stay invested in uptrends (buffered 200-day rule) and also buy deep oversold dips."""
    t = sma_trend_buffer(df, n, band)
    d = rsi2_pullback(df)
    out = t.copy()
    out["position"] = np.fmax(t["position"], d["position"]).where(t["position"].notna())
    return out


STRATEGIES = {
    "buy_hold": buy_hold,
    "score": score,
    "sma_trend": sma_trend,
    "sma_trend_buffer": sma_trend_buffer,
    "golden_cross": golden_cross,
    "momentum_12m": momentum_12m,
    "donchian": donchian,
    "rsi2_pullback": rsi2_pullback,
    "trend_or_dip": trend_or_dip,
}


# ---------------------------------------------------------------------------
# Live signals: explain the latest bar in plain English
# ---------------------------------------------------------------------------
TITLES = {
    "sma_trend_buffer": "200-day trend rule (3% buffer)",
    "sma_trend": "200-day trend rule",
    "trend_or_dip": "Trend + dip buying",
    "golden_cross": "Golden cross (50/200)",
    "momentum_12m": "12-month momentum",
    "donchian": "Breakout (55/20 day)",
    "rsi2_pullback": "Short-term dip buying",
    "score": "4-indicator score",
    "buy_hold": "Buy and hold",
}


def _fmt(p: float) -> str:
    return f"{p:,.0f}" if p >= 1000 else f"{p:,.2f}" if p >= 10 else f"{p:.4f}"


def _trend_lines(row, invested: bool, band: float) -> list[str]:
    pct = row.Close / row.sma - 1
    lines = [f"Price is {abs(pct):.1%} {'above' if pct >= 0 else 'below'} its 200-day average ({_fmt(row.sma)})"]
    if invested:
        lines.append(f"Sell trigger: a daily close below {_fmt(row.sma * (1 - band))}")
    else:
        lines.append(f"Buy trigger: a daily close above {_fmt(row.sma)}")
    return lines


def explain(name: str, out: pd.DataFrame) -> list[str]:
    row = out.iloc[-1]
    invested = row.position == 1
    if name in ("sma_trend_buffer", "trend_or_dip"):
        return _trend_lines(row, invested, 0.03)
    if name == "sma_trend":
        return _trend_lines(row, invested, 0.0)
    if name == "golden_cross":
        return [f"50-day average {'above' if row.sma_fast > row.sma_slow else 'below'} 200-day "
                f"({_fmt(row.sma_fast)} vs {_fmt(row.sma_slow)})"]
    if name == "momentum_12m":
        return [f"Price is {row.mom:+.1%} vs 12 months ago"]
    if name == "rsi2_pullback":
        return [f"Short-term RSI(2) is {row.rsi2:.0f}; 200-day average {_fmt(row.sma)}"]
    if name == "donchian":
        hi = out["Close"].rolling(55).max().iloc[-2]
        lo = out["Close"].rolling(20).min().iloc[-2]
        return [f"Buy trigger: close above {_fmt(hi)} (55-day high)" if not invested
                else f"Sell trigger: close below {_fmt(lo)} (20-day low)"]
    if name == "score":
        return [f"Indicator score {int(row.score):+d} of 4"]
    return []


def latest(symbol: str, df: pd.DataFrame, name: str):
    """Signal for the most recent completed bar, or None if not enough history."""
    from .strategy import Signal

    out = STRATEGIES[name](df).dropna(subset=["position"])
    if out.empty:
        return None
    row = out.iloc[-1]
    changed = len(out) > 1 and out["position"].iloc[-2] != row.position
    reasons = explain(name, out)
    if changed:
        reasons.insert(0, "Signal changed at today's close")
    return Signal(
        symbol=symbol,
        action=BUY if row.position == 1 else SELL,
        score=0,
        price=float(row.Close),
        date=str(pd.Timestamp(out.index[-1]).date()),
        reasons=reasons,
    )
