"""Send alerts via Telegram (falls back to printing when not configured)."""
import os
import time

import requests

from .strategy import BUY, SELL, Signal

EMOJI = {BUY: "🟢", SELL: "🔴"}


def configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def fmt_price(p: float) -> str:
    if p >= 1000:
        return f"{p:,.0f}"
    if p >= 10:
        return f"{p:,.2f}"
    return f"{p:.4f}"


def format_signal(sig: Signal, previous: str | None = None) -> str:
    head = f"{EMOJI.get(sig.action, '⚪')} *{sig.action}* {sig.symbol} @ {fmt_price(sig.price)}"
    lines = [head, f"Score {sig.score:+d}/4 · bar {sig.date}"]
    if previous:
        lines.append(f"Changed from {previous}")
    lines += [f"• {r}" for r in sig.reasons]
    return "\n".join(lines)


def send(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    print(text, end="\n\n")
    if not token or not chat_id:
        print("(Telegram not configured — printed only)")
        return False
    last_err = ""
    for attempt in range(4):
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=20,
            )
        except requests.RequestException as e:  # network blip: retry
            last_err = str(e)
        else:
            if resp.ok:
                return True
            last_err = f"{resp.status_code}: {resp.text}"
            if resp.status_code < 500 and resp.status_code != 429:
                break  # bad token / chat id: retrying won't help
        time.sleep(2 ** attempt)
    print(f"Telegram error {last_err}")
    return False
