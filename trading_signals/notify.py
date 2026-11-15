"""Send alerts via Telegram (falls back to printing when not configured)."""
import os

import requests

from .strategy import BUY, SELL, Signal

EMOJI = {BUY: "🟢", SELL: "🔴"}


def format_signal(sig: Signal, previous: str | None = None) -> str:
    head = f"{EMOJI.get(sig.action, '⚪')} *{sig.action}* {sig.symbol} @ {sig.price:,.4g}"
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
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=20,
    )
    if not resp.ok:
        print(f"Telegram error {resp.status_code}: {resp.text}")
    return resp.ok
