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
