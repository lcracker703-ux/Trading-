"""Combine indicators into a BUY / SELL / HOLD signal.

Score components (each -1, 0 or +1):
  trend   : close above / below the slow SMA (long-term trend)
  cross   : fast SMA above / below slow SMA (golden / death cross regime)
  macd    : MACD line above / below its signal line (momentum)
  rsi     : oversold (+1) / overbought (-1), neutral otherwise
Score ranges from -4 to +4.
"""
from dataclasses import dataclass, field

import pandas as pd

from . import indicators as ind

BUY, SELL, HOLD = "BUY", "SELL", "HOLD"


@dataclass
class StrategyConfig:
    sma_fast: int = 50
    sma_slow: int = 200
    rsi_period: int = 14
    rsi_oversold: float = 30
    rsi_overbought: float = 70
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    buy_threshold: int = 2
    sell_threshold: int = -2

    @classmethod
    def from_dict(cls, d: dict | None) -> "StrategyConfig":
        d = d or {}
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Signal:
    symbol: str
    action: str
    score: int
    price: float
    date: str
    reasons: list[str] = field(default_factory=list)
    rsi: float | None = None
    agree: int = 0  # how many of the 4 checks point the same way as the signal


def _sign(cond_pos: pd.Series, cond_neg: pd.Series) -> pd.Series:
    return cond_pos.astype(int) - cond_neg.astype(int)


def analyze(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """Return df with indicator, score and action columns. Needs a 'Close' column."""
    out = df.copy()
    close = out["Close"]
    out["sma_fast"] = ind.sma(close, cfg.sma_fast)
    out["sma_slow"] = ind.sma(close, cfg.sma_slow)
    out["rsi"] = ind.rsi(close, cfg.rsi_period)
    out = out.join(ind.macd(close, cfg.macd_fast, cfg.macd_slow, cfg.macd_signal))

    out["s_trend"] = _sign(close > out["sma_slow"], close < out["sma_slow"])
    out["s_cross"] = _sign(out["sma_fast"] > out["sma_slow"], out["sma_fast"] < out["sma_slow"])
    out["s_macd"] = _sign(out["macd"] > out["macd_signal"], out["macd"] < out["macd_signal"])
    out["s_rsi"] = _sign(out["rsi"] < cfg.rsi_oversold, out["rsi"] > cfg.rsi_overbought)
    out["score"] = out[["s_trend", "s_cross", "s_macd", "s_rsi"]].sum(axis=1)

    ready = out[["sma_slow", "rsi", "macd_signal"]].notna().all(axis=1)
    action = pd.Series(HOLD, index=out.index)
    action[out["score"] >= cfg.buy_threshold] = BUY
    action[out["score"] <= cfg.sell_threshold] = SELL
    out["action"] = action.where(ready, None)
    return out


def latest_signal(symbol: str, df: pd.DataFrame, cfg: StrategyConfig) -> Signal | None:
    a = analyze(df, cfg).dropna(subset=["action"])
    if a.empty:
        return None
    row, prev = a.iloc[-1], a.iloc[-2] if len(a) > 1 else None
    reasons = [
        "Long-term trend is UP (price above its 200-day average)" if row.s_trend > 0
        else "Long-term trend is DOWN (price below its 200-day average)",
    ]
    cross_just = prev is not None and prev.s_cross != row.s_cross
    if row.s_cross > 0:
        reasons.append("Golden cross" + (" just happened" if cross_just else "") + " (50-day average above 200-day)")
    elif row.s_cross < 0:
        reasons.append("Death cross" + (" just happened" if cross_just else "") + " (50-day average below 200-day)")
    macd_just = prev is not None and prev.s_macd != row.s_macd
    if row.s_macd > 0:
        reasons.append("Momentum is rising" + (" (just turned up)" if macd_just else ""))
    elif row.s_macd < 0:
        reasons.append("Momentum is falling" + (" (just turned down)" if macd_just else ""))
    if row.s_rsi > 0:
        reasons.append(f"Oversold, may bounce (RSI {row.rsi:.0f})")
    elif row.s_rsi < 0:
        reasons.append(f"Overbought, may pull back (RSI {row.rsi:.0f})")
    else:
        reasons.append(f"Not overbought or oversold (RSI {row.rsi:.0f})")
    return Signal(
        symbol=symbol,
        action=row.action,
        score=int(row.score),
        price=float(row.Close),
        date=str(pd.Timestamp(a.index[-1]).date()),
        reasons=reasons,
        rsi=float(row.rsi),
        agree=int(sum(1 for c in ("s_trend", "s_cross", "s_macd", "s_rsi")
                      if row[c] != 0 and (row[c] > 0) == (row.score > 0))),
    )
