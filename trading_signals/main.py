"""Run the watchlist, alert on signal changes.

  python -m trading_signals.main            # alert only when a signal changes
  python -m trading_signals.main --report   # also send a full summary of every symbol
"""
import argparse
import json
import os
import sys
from pathlib import Path

import yaml

from . import data, notify
from .strategy import HOLD, StrategyConfig, latest_signal


def load_state(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def run(config_path: str, state_path: str, report: bool = False, fetch=data.fetch_daily) -> list:
    cfg = yaml.safe_load(Path(config_path).read_text())
    strat = StrategyConfig.from_dict(cfg.get("strategy"))
    state_file = Path(state_path)
    state = load_state(state_file)
    alerts, summary, errors = [], [], []

    for symbol in cfg["watchlist"]:
        try:
            sig = latest_signal(symbol, fetch(symbol, cfg.get("history_period", "2y")), strat)
        except Exception as e:  # keep going on bad symbols / network blips
            errors.append(f"{symbol}: {e}")
            continue
        if sig is None:
            errors.append(f"{symbol}: not enough history")
            continue
        prev = state.get(symbol, {}).get("action")
        summary.append(f"{notify.EMOJI.get(sig.action, '⚪')} {notify.display_name(symbol)}: {sig.action} ({sig.score:+d}) @ {notify.fmt_price(sig.price)}")
        # Alert on a change into BUY or SELL (first run seeds state without spamming HOLDs)
        if sig.action != prev and sig.action != HOLD:
            sent = notify.send(notify.format_signal(sig, prev))
            if notify.configured() and not sent:
                errors.append(f"{symbol}: alert failed to send, will retry next run")
                continue  # don't remember it, so the alert is retried
            alerts.append(sig)
        state[symbol] = {"action": sig.action, "score": sig.score, "date": sig.date, "price": sig.price}

    if report:
        notify.send("📊 *Daily summary*\n" + "\n".join(summary) + ("\n\n⚠️ " + "\n".join(errors) if errors else ""))
    elif errors:
        print("Errors:\n" + "\n".join(errors))
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    if notify.configured() and any("failed to send" in e for e in errors):
        raise SystemExit("Some Telegram alerts failed to send — see 'Telegram error' lines above")
    return alerts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--state", default="state.json")
    p.add_argument("--report", action="store_true", help="send full summary too")
    a = p.parse_args()
    if os.environ.get("GITHUB_ACTIONS") and not notify.configured():
        sys.exit("TELEGRAM_BOT_TOKEN and/or TELEGRAM_CHAT_ID secret is missing or empty")
    run(a.config, a.state, a.report)


if __name__ == "__main__":
    main()
