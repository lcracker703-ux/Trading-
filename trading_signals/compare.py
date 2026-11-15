"""Compare every strategy across many symbols, split into a training period and an
unseen test period (to avoid picking a strategy that only fits the past by luck).

  python -m trading_signals.compare --split 2021-01-01
"""
import argparse
import os

import numpy as np
import pandas as pd

from .strategies import STRATEGIES

DEFAULT_UNIVERSE = [
    # stocks / indices
    "AAPL", "MSFT", "AMZN", "JPM", "XOM", "SPY", "QQQ", "IWM", "EFA", "EWU",
    # crypto
    "BTC-USD", "ETH-USD",
    # forex / commodities
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "GLD",
]


def metrics(close: pd.Series, position: pd.Series, fee: float = 0.001, ppy: float = 252) -> dict:
    pos = position.shift(1).fillna(0)  # trade on the bar after the signal
    ret = close.pct_change().fillna(0)
    trades = pos.diff().abs().fillna(0)
    strat = pos * ret - trades * fee
    eq = (1 + strat).cumprod()
    years = max(len(eq) / ppy, 1e-9)
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = strat.std() * np.sqrt(ppy)
    return {
        "cagr": cagr,
        "mdd": (eq / eq.cummax() - 1).min(),
        "sharpe": strat.mean() * ppy / vol if vol > 0 else 0.0,
        "trades_per_yr": trades.sum() / years,
        "exposure": pos.mean(),
    }


def evaluate(df: pd.DataFrame, split: str) -> dict:
    """{strategy: {"train": metrics, "test": metrics}} for one symbol."""
    ppy = 365 if (df.index.day_of_week >= 5).any() else 252  # crypto trades weekends
    res = {}
    for name, fn in STRATEGIES.items():
        p = fn(df)
        valid = p["position"].notna()
        p = p[valid]
        idx = p.index.tz_localize(None) if p.index.tz is not None else p.index
        cut = idx < pd.Timestamp(split)
        res[name] = {}
        for label, mask in (("train", cut), ("test", ~cut)):
            seg = p[mask]
            if len(seg) > ppy:  # need at least a year
                res[name][label] = metrics(seg["Close"], seg["position"], ppy=ppy)
    return res


def summarise(all_res: dict) -> str:
    rows = []
    for name in STRATEGIES:
        for period in ("train", "test"):
            vals = [r[name][period] for r in all_res.values() if period in r[name]]
            bh = [r["buy_hold"][period] for r in all_res.values() if period in r[name]]
            if not vals:
                continue
            rows.append({
                "strategy": name, "period": period, "n": len(vals),
                "cagr": np.median([v["cagr"] for v in vals]),
                "sharpe": np.median([v["sharpe"] for v in vals]),
                "mdd": np.median([v["mdd"] for v in vals]),
                "beat_sharpe": sum(v["sharpe"] > b["sharpe"] for v, b in zip(vals, bh)),
                "beat_cagr": sum(v["cagr"] > b["cagr"] for v, b in zip(vals, bh)),
                "better_dd": sum(v["mdd"] > b["mdd"] for v, b in zip(vals, bh)),
                "trades": np.median([v["trades_per_yr"] for v in vals]),
                "exposure": np.median([v["exposure"] for v in vals]),
            })
    t = pd.DataFrame(rows)
    lines = []
    for period in ("train", "test"):
        s = t[t.period == period].sort_values("sharpe", ascending=False)
        lines.append(f"\n## {period.upper()} period — medians across symbols\n")
        lines.append("| strategy | CAGR | Sharpe | max DD | beat B&H Sharpe | beat B&H return | smaller DD | trades/yr | invested |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in s.itertuples():
            lines.append(
                f"| {r.strategy} | {r.cagr:.1%} | {r.sharpe:.2f} | {r.mdd:.0%} | {r.beat_sharpe}/{r.n} | "
                f"{r.beat_cagr}/{r.n} | {r.better_dd}/{r.n} | {r.trades:.1f} | {r.exposure:.0%} |"
            )
    return "\n".join(lines)


def per_symbol(all_res: dict, period: str) -> str:
    names = list(STRATEGIES)
    lines = [f"\n## {period.upper()} Sharpe by symbol\n", "| symbol | " + " | ".join(names) + " |",
             "|---" * (len(names) + 1) + "|"]
    for sym, r in all_res.items():
        cells = [f"{r[n][period]['sharpe']:.2f}" if period in r[n] else "-" for n in names]
        lines.append(f"| {sym} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    from .data import fetch_daily

    p = argparse.ArgumentParser()
    p.add_argument("symbols", nargs="*")
    p.add_argument("--split", default="2021-01-01")
    p.add_argument("--period", default="max")
    a = p.parse_args()
    all_res = {}
    for s in a.symbols or DEFAULT_UNIVERSE:
        try:
            df = fetch_daily(s, a.period)
            df = df[df.index >= df.index[-1] - pd.DateOffset(years=25)]
            all_res[s] = evaluate(df, a.split)
            print(f"{s}: {df.index[0].date()} → {df.index[-1].date()}")
        except Exception as e:
            print(f"{s}: FAILED {e}")
    report = (f"# Strategy comparison (train < {a.split} ≤ test)\n"
              + summarise(all_res) + per_symbol(all_res, "train") + per_symbol(all_res, "test"))
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(report + "\n")


if __name__ == "__main__":
    main()
