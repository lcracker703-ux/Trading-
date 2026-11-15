"""Check your setup: Telegram secrets, config.yaml and that every symbol downloads.

  python -m trading_signals.check
"""
import sys

import yaml

from . import notify
from .data import fetch_daily
from .strategies import STRATEGIES


def main():
    problems, ok = [], []
    try:
        cfg = yaml.safe_load(open("config.yaml")) or {}
        ok.append("config.yaml loaded")
    except Exception as e:
        sys.exit(f"❌ config.yaml can't be read: {e}")

    name = (cfg.get("strategy") or {}).get("name", "sma_trend_buffer")
    if name in STRATEGIES:
        ok.append(f"Strategy: {name}")
    else:
        problems.append(f"Unknown strategy '{name}'. Options: {', '.join(STRATEGIES)}")

    for s in cfg.get("watchlist") or []:
        try:
            df = fetch_daily(s, cfg.get("history_period", "2y"))
            if len(df) < 260:
                problems.append(f"{s}: only {len(df)} days of history (need ~1 year)")
            else:
                ok.append(f"{s}: data OK")
        except Exception as e:
            problems.append(f"{s}: can't download — check the symbol on finance.yahoo.com ({e})")
    if not cfg.get("watchlist"):
        problems.append("watchlist in config.yaml is empty")

    if not notify.configured():
        problems.append("TELEGRAM_BOT_TOKEN and/or TELEGRAM_CHAT_ID secret missing")

    text = "🔧 *Setup check*\n\n" + "\n".join(f"✅ {o}" for o in ok)
    if problems:
        text += "\n\n" + "\n".join(f"❌ {p}" for p in problems)
    else:
        text += "\n\n🎉 Everything works. Daily alerts are on."
    sent = notify.send(text)
    if notify.configured() and not sent:
        problems.append("Telegram rejected the message — see the error above. Check the chat ID "
                        "is YOUR id (from @userinfobot), not the bot's, and that you've messaged the bot.")
    if problems:
        sys.exit("\n".join(problems))


if __name__ == "__main__":
    main()
