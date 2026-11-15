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
    from trading_signals.backtest import format_result

    r = backtest(frame(trend(True)), "score")
    assert r["trades"] >= 1 and r["strategy_return"] > 0
    assert r["years"] < 1.2  # starts after the 200-day warm-up
    assert "$1,000 buy & hold" in format_result("AAPL", r)


def test_run_alerts_only_on_change(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    sent = []
    monkeypatch.setattr("trading_signals.notify.send", lambda t: sent.append(t) or False)
    cfg = tmp_path / "c.yaml"
    cfg.write_text("watchlist: [UP, DN]\n")
    state = tmp_path / "s.json"
    data = {"UP": frame(trend(True)), "DN": frame(trend(False))}
    fetch = lambda s, p: data[s]
    # First run: no per-symbol alerts, just a "now tracking" summary
    assert run(str(cfg), str(state), fetch=fetch) == []
    assert len(sent) == 1 and "Now tracking" in sent[0]
    assert run(str(cfg), str(state), fetch=fetch) == []  # no change -> no alert
    data["UP"] = frame(trend(False, seed=5))
    alerts = run(str(cfg), str(state), fetch=fetch)
    assert [a.action for a in alerts] == [SELL] and "Time to SELL" in sent[-1]
    assert json.loads(state.read_text())["UP"]["action"] == SELL


def test_every_strategy_runs_and_explains():
    from trading_signals.strategies import STRATEGIES, latest

    for name in STRATEGIES:
        for up in (True, False):
            sig = latest("AAPL", frame(trend(up, n=400)), name)
            assert sig is not None and sig.action in (BUY, SELL), name


def test_trend_rule_gives_trigger_levels():
    from trading_signals.notify import format_signal, summary_line
    from trading_signals.strategies import latest

    up = latest("AAPL", frame(trend(True)), "sma_trend_buffer")
    dn = latest("AAPL", frame(trend(False)), "sma_trend_buffer")
    assert up.action == BUY and any("Sell trigger" in r for r in up.reasons)
    assert dn.action == SELL and any("Buy trigger" in r for r in dn.reasons)
    assert "Time to BUY Apple (AAPL)" in format_signal(up)
    assert "sell trigger" in summary_line(up).lower()


def test_compare_runs():
    from trading_signals.compare import evaluate, summarise

    r = {"X": evaluate(frame(trend(True, n=1500)), "2024-01-01")}
    assert "sma_trend_buffer" in summarise(r)


def test_send_retries_network_errors(monkeypatch):
    import requests
    from trading_signals import notify

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setattr(notify.time, "sleep", lambda s: None)
    calls = []

    class Ok:
        ok, status_code, text = True, 200, ""

    def post(*a, **k):
        calls.append(1)
        if len(calls) < 3:
            raise requests.ConnectionError("reset")
        return Ok()

    monkeypatch.setattr(notify.requests, "post", post)
    assert notify.send("hi") is True and len(calls) == 3
