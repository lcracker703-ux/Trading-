import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from trading_signals import indicators as ind
from trading_signals.backtest import backtest
from trading_signals.data import drop_incomplete_bar
from trading_signals.main import run
from trading_signals.strategy import BUY, SELL, StrategyConfig, analyze, latest_signal


def frame(prices, end="2024-12-31"):
    idx = pd.date_range(end=end, periods=len(prices), freq="D", tz="UTC")
    return pd.DataFrame({"Close": prices}, index=idx)


def trend(up: bool, n=400, seed=0):
    """Trend with a counter-move then resumption at the end (realistic MACD/RSI)."""
    rng = np.random.default_rng(seed)
    d = 1 if up else -1
    drift = np.r_[np.full(n - 40, 0.003 * d), np.full(20, -0.004 * d), np.full(20, 0.004 * d)]
    return 100 * np.exp(np.cumsum(drift + rng.normal(0, 0.004, n)))


def test_rsi_bounds_and_extremes():
    r = ind.rsi(pd.Series(trend(True)), 14).dropna()
    assert ((r >= 0) & (r <= 100)).all()
    assert ind.rsi(pd.Series(np.arange(1, 50, dtype=float)), 14).iloc[-1] == 100


def test_uptrend_buy_downtrend_sell():
    cfg = StrategyConfig()
    assert latest_signal("UP", frame(trend(True)), cfg).action == BUY
    assert latest_signal("DN", frame(trend(False)), cfg).action == SELL


def test_not_enough_history():
    assert latest_signal("X", frame(trend(True, n=100)), StrategyConfig()) is None


def test_score_range():
    a = analyze(frame(trend(True, seed=3)), StrategyConfig())
    assert a["score"].between(-4, 4).all()


def test_drop_incomplete_bar():
    df = frame(np.arange(1.0, 6.0), end="2024-06-10")
    assert len(drop_incomplete_bar(df, datetime(2024, 6, 10, 15, tzinfo=timezone.utc))) == 4
    assert len(drop_incomplete_bar(df, datetime(2024, 6, 11, 1, tzinfo=timezone.utc))) == 5


def test_backtest_runs():
    r = backtest(frame(trend(True)), StrategyConfig())
    assert r["trades"] >= 1 and r["strategy_return"] > 0


def test_run_alerts_only_on_change(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    cfg = tmp_path / "c.yaml"
    cfg.write_text("watchlist: [UP, DN]\n")
    state = tmp_path / "s.json"
    data = {"UP": frame(trend(True)), "DN": frame(trend(False))}
    fetch = lambda s, p: data[s]
    assert {a.symbol for a in run(str(cfg), str(state), fetch=fetch)} == {"UP", "DN"}
    assert run(str(cfg), str(state), fetch=fetch) == []  # no change -> no alert
    data["UP"] = frame(trend(False, seed=5))
    assert [a.action for a in run(str(cfg), str(state), fetch=fetch)] == [SELL]
    assert json.loads(state.read_text())["UP"]["action"] == SELL
