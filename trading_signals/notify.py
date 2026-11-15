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


NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "SPY": "S&P 500 ETF", "TSLA": "Tesla",
    "NVDA": "Nvidia", "AMZN": "Amazon", "GOOGL": "Google", "META": "Meta",
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana", "GC=F": "Gold",
}


def display_name(symbol: str) -> str:
    if symbol in NAMES:
        return f"{NAMES[symbol]} ({symbol})"
    if symbol.endswith("=X") and len(symbol) == 8:
        return f"{symbol[:3]}/{symbol[3:6]}"
    return symbol


STRENGTH = {2: "Moderate", 3: "Strong", 4: "Very strong"}


def format_signal(sig: Signal, previous: str | None = None) -> str:
    name = display_name(sig.symbol)
    strength = STRENGTH.get(abs(sig.score), "Weak")
    if sig.action == BUY:
        head = f"🟢 *Time to BUY {name}*"
        verb = "Consider buying"
    else:
        head = f"🔴 *Time to SELL {name}*"
        verb = "Consider selling (or not buying)"
    lines = [
        head,
        f"{verb} at around {fmt_price(sig.price)}",
        f"Signal strength: {strength} ({sig.agree} of 4 checks agree)",
        "",
        "*Why:*",
        *[f"• {r}" for r in sig.reasons],
    ]
    if previous:
        lines += ["", f"_Was {previous} before. Based on the {sig.date} daily close._"]
    else:
        lines += ["", f"_Based on the {sig.date} daily close._"]
    lines.append("_Not financial advice. Do your own checks before trading._")
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
