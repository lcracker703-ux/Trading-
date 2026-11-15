"""Backtest the strategy: long on BUY, flat on SELL, vs buy-and-hold.

  python -m trading_signals.backtest AAPL BTC-USD --period 10y
"""
import argparse

import pandas as pd
import yaml

from .strategy import BUY, SELL, StrategyConfig, analyze


def backtest(df: pd.DataFrame, cfg: StrategyConfig, fee: float = 0.001) -> dict:
    a = analyze(df, cfg)
    pos, positions = 0, []
    for act in a["action"]:
        if act == BUY:
            pos = 1
        elif act == SELL:
            pos = 0
        positions.append(pos)
    # Act on the next bar (signal known only at close)
    position = pd.Series(positions, index=a.index).shift(1).fillna(0)
    ret = a["Close"].pct_change().fillna(0)
    trades = position.diff().abs().fillna(0)
    strat = position * ret - trades * fee
    eq, bh = (1 + strat).cumprod(), (1 + ret).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    return {
        "strategy_return": eq.iloc[-1] - 1,
        "buy_hold_return": bh.iloc[-1] - 1,
        "max_drawdown": dd,
        "buy_hold_drawdown": (bh / bh.cummax() - 1).min(),
        "trades": int(trades.sum()),
        "time_in_market": position.mean(),
    }


def main():
    from .data import fetch_daily

    p = argparse.ArgumentParser()
    p.add_argument("symbols", nargs="*")
    p.add_argument("--period", default="10y")
    p.add_argument("--config", default="config.yaml")
    a = p.parse_args()
    cfg = yaml.safe_load(open(a.config))
    strat = StrategyConfig.from_dict(cfg.get("strategy"))
    for s in a.symbols or cfg["watchlist"]:
        r = backtest(fetch_daily(s, a.period), strat)
        print(
            f"{s:10} strategy {r['strategy_return']:+8.1%}  buy&hold {r['buy_hold_return']:+8.1%}  "
            f"maxDD {r['max_drawdown']:+6.1%} (B&H {r['buy_hold_drawdown']:+6.1%})  "
            f"trades {r['trades']:3d}  in-market {r['time_in_market']:.0%}"
        )


if __name__ == "__main__":
    main()
