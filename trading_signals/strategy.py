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
    reasons = []
    reasons.append(
        f"Price {'above' if row.s_trend > 0 else 'below'} {cfg.sma_slow}-day SMA "
        f"({'uptrend' if row.s_trend > 0 else 'downtrend'})"
    )
    regime = "golden cross" if row.s_cross > 0 else "death cross"
    just = prev is not None and prev.s_cross != row.s_cross
    reasons.append(f"{cfg.sma_fast}/{cfg.sma_slow} SMA: {regime}{' (just crossed!)' if just else ''}")
    mjust = prev is not None and prev.s_macd != row.s_macd
    reasons.append(
        f"MACD {'bullish' if row.s_macd > 0 else 'bearish'}{' (fresh crossover)' if mjust else ''}"
    )
    rsi_txt = "oversold" if row.s_rsi > 0 else "overbought" if row.s_rsi < 0 else "neutral"
    reasons.append(f"RSI {row.rsi:.1f} ({rsi_txt})")
    return Signal(
        symbol=symbol,
        action=row.action,
        score=int(row.score),
        price=float(row.Close),
        date=str(pd.Timestamp(a.index[-1]).date()),
        reasons=reasons,
        rsi=float(row.rsi),
    )
