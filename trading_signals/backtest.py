"""Backtest the strategy: buy on BUY, sell on SELL, vs simply buying and holding.

  python -m trading_signals.backtest AAPL BTC-USD --period 10y
  python -m trading_signals.backtest --telegram        # whole watchlist, results to Telegram
"""
import argparse

import pandas as pd
import yaml

from . import notify
from .strategy import BUY, SELL, StrategyConfig, analyze


def backtest(df: pd.DataFrame, cfg: StrategyConfig, fee: float = 0.001) -> dict:
    # Start once indicators are ready (needs ~200 days), so both sides cover the same period
    a = analyze(df, cfg).dropna(subset=["action"])
    pos, positions = 0, []
    for act in a["action"]:
        if act == BUY:
            pos = 1
        elif act == SELL:
            pos = 0
        positions.append(pos)
    # Act on the next bar (signal known only at the close)
    position = pd.Series(positions, index=a.index, dtype=float).shift(1).fillna(0)
    ret = a["Close"].pct_change().fillna(0)
    trades = position.diff().abs().fillna(0)
    strat = position * ret - trades * fee
    eq, bh = (1 + strat).cumprod(), (1 + ret).cumprod()

    # Win rate of completed round trips (buy -> sell)
    wins = total = 0
    entry_eq = None
    for i in range(len(position)):
        if position.iloc[i] == 1 and (i == 0 or position.iloc[i - 1] == 0):
            entry_eq = eq.iloc[i - 1] if i > 0 else 1.0
        if position.iloc[i] == 0 and i > 0 and position.iloc[i - 1] == 1 and entry_eq is not None:
            total += 1
            wins += eq.iloc[i] > entry_eq
            entry_eq = None

    return {
        "start": str(pd.Timestamp(a.index[0]).date()),
        "end": str(pd.Timestamp(a.index[-1]).date()),
        "years": (a.index[-1] - a.index[0]).days / 365.25,
        "strategy_return": eq.iloc[-1] - 1,
        "buy_hold_return": bh.iloc[-1] - 1,
        "max_drawdown": (eq / eq.cummax() - 1).min(),
        "buy_hold_drawdown": (bh / bh.cummax() - 1).min(),
        "trades": int(trades.sum()),
        "round_trips": total,
        "win_rate": wins / total if total else None,
        "time_in_market": position.mean(),
    }


def format_result(symbol: str, r: dict) -> str:
    s_val, b_val = 1000 * (1 + r["strategy_return"]), 1000 * (1 + r["buy_hold_return"])
    verdict = "✅ Signals beat buy & hold" if s_val > b_val else "❌ Buy & hold did better"
    win = f"{r['win_rate']:.0%} of {r['round_trips']} trades made money" if r["win_rate"] is not None else "no completed trades"
    return "\n".join([
        f"*{notify.display_name(symbol)}* ({r['start'][:4]}–{r['end'][:4]}, {r['years']:.1f} yrs)",
        f"$1,000 following signals → *${s_val:,.0f}*",
        f"$1,000 buy & hold → *${b_val:,.0f}*",
        f"Worst drop: signals {r['max_drawdown']:.0%} vs hold {r['buy_hold_drawdown']:.0%}",
        f"{win} · invested {r['time_in_market']:.0%} of the time",
        verdict,
    ])


def main():
    from .data import fetch_daily

    p = argparse.ArgumentParser()
    p.add_argument("symbols", nargs="*")
    p.add_argument("--period", default="10y")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--telegram", action="store_true", help="send results to Telegram")
    a = p.parse_args()
    cfg = yaml.safe_load(open(a.config))
    strat = StrategyConfig.from_dict(cfg.get("strategy"))
    blocks, beat, n = [], 0, 0
    for s in a.symbols or cfg["watchlist"]:
        try:
            r = backtest(fetch_daily(s, a.period), strat)
        except Exception as e:
            blocks.append(f"*{s}*: couldn't test ({e})")
            continue
        n += 1
        beat += r["strategy_return"] > r["buy_hold_return"]
        blocks.append(format_result(s, r))
    text = (
        f"🧪 *Backtest: last {a.period}*\n_Buy on BUY, sell on SELL, 0.1% fee per trade_\n\n"
        + "\n\n".join(blocks)
        + f"\n\n*Overall:* signals beat buy & hold on {beat} of {n} symbols.\n"
        "_Past results don't guarantee future returns._"
    )
    if a.telegram:
        if not notify.send(text):
            raise SystemExit("Failed to send backtest results to Telegram")
    else:
        print(text)


if __name__ == "__main__":
    main()
