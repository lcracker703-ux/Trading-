# Trend Alerts: free trading signals on Telegram

Get a Telegram message when a stock, ETF, crypto or forex pair turns **BUY** or **SELL**, plus a daily summary. It runs free on GitHub, with no server, no subscription and no coding needed.

> ⚠️ **Not financial advice.** Read [DISCLAIMER.md](DISCLAIMER.md). In honest testing, no strategy here beat simply buying and holding on return; the default strategy aims to **reduce big losses**. See [docs/RESULTS.md](docs/RESULTS.md).

**Example alert:**

> 🟢 **Time to BUY Apple (AAPL)**
> Consider buying at around 356.27
>
> **Why:**
> • Price is 18.5% above its 200-day average (300.77)
> • Sell trigger: a daily close below 291.75
>
> _Based on the 2026-11-13 daily close · strategy: 200-day trend rule (3% buffer)._

---

## Setup (about 10 minutes, works on a phone or iPad)

You need a free GitHub account and a free Telegram account.

### 1. Get your own copy
On this repository's GitHub page, tap **Use this template** → **Create a new repository**. If you don't see that button, tap **Fork** instead.

> On a phone or iPad, use Safari or Chrome. If you can't find a button, tap **aA → Request Desktop Website**.

### 2. Create your Telegram bot
1. In Telegram, open **@BotFather** and send `/newbot`.
2. Choose a name and a username ending in `bot`.
3. BotFather replies with a **token** that looks like `1234567890:AAE...`. Keep it private. Never paste it in a chat or post it publicly.
4. Open your new bot and send it any message, e.g. "hi". The bot won't reply, which is normal; it just needs permission to message you.

### 3. Get your chat ID
In Telegram, open **@userinfobot** and send it any message. It replies with your **Id**, a number like `123456789`.

> ⚠️ Use **your** Id. The number at the start of the token belongs to the bot, and using it gives the error "the bot can't send messages to the bot".

### 4. Add your two secrets
In your copy on GitHub, go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the whole token, including the part after the colon |
| `TELEGRAM_CHAT_ID` | your Id number from @userinfobot |

### 5. Turn on Actions and check
1. Open the **Actions** tab. If GitHub asks, tap **I understand my workflows, go ahead and enable them**.
2. Choose **Check setup** → **Run workflow**.
3. Within about a minute, you'll get a 🔧 **Setup check** message in Telegram listing anything that needs fixing.

That's it. Every day at 05:37 UTC you'll get a 📊 summary, plus a "Time to BUY / SELL" alert whenever a signal changes.

---

## Customise

Edit **`config.yaml`** in GitHub (tap the file, then the ✏️ pencil):

- **`watchlist`** is your list of symbols. Any symbol from [Yahoo Finance](https://finance.yahoo.com) works. For example:
  - stocks: `AAPL`, `VUSA.L` (London), `NPN.JO` (Johannesburg)
  - crypto: `BTC-USD`
  - forex: `EURUSD=X`
- **`strategy: name`** chooses the rule. See the table below.

| Strategy | In plain English |
|---|---|
| `sma_trend_buffer` (default) | Hold while the price is above its 200-day average. Sell only on a close 3% below it. |
| `trend_or_dip` | The same, plus buys sharp short-term dips during uptrends |
| `sma_trend` | Hold above the 200-day average, sell below it, with no buffer (more trades) |
| `golden_cross` | Hold while the 50-day average is above the 200-day |
| `momentum_12m` | Hold while the price is higher than 12 months ago |
| `donchian` | Buy a new 55-day high, sell a new 20-day low |
| `rsi2_pullback` | Buy short dips in uptrends, sell on the bounce (in the market ~10% of the time) |
| `score` | The original 4-indicator score (trend, golden cross, MACD, RSI) |

**To change the alert time,** edit the `cron:` line in `.github/workflows/signals.yml`. The time is in UTC.

## Workflows (Actions tab)

| Workflow | What it does |
|---|---|
| **Trading signals** | Runs daily and sends the summary and any BUY/SELL alerts. You can also run it by hand at any time. |
| **Check setup** | Tests your Telegram secrets and every symbol, then reports in Telegram |
| **Backtest** | Shows what $1,000 would have become following the signals vs buying and holding, sent to Telegram |
| **Compare strategies** | Tests every strategy on 16 markets, split into training and unseen test periods |

## How it works

- Prices are daily closes from Yahoo Finance. Today's unfinished candle is ignored, so signals don't flicker.
- An alert is sent only when a symbol's signal **changes**. The last signal for each symbol is saved in `state.json`.
- Failed Telegram messages are retried, and the run shows a red ❌ on GitHub if alerts can't be delivered.

## Run on a computer (optional)

```bash
pip install -r requirements.txt
python -m trading_signals.main --report            # prints the signals (or sends them, if TELEGRAM_* env vars are set)
python -m trading_signals.backtest AAPL --period 10y
python -m trading_signals.compare                  # full strategy comparison
pytest
```
