# Trading signals

Analyses trends in stocks, ETFs, crypto and forex, and sends you a **Telegram alert when a symbol turns BUY or SELL**. It runs free on GitHub Actions once a day.

> ⚠️ These are mechanical technical-analysis signals, not financial advice. Run the backtest before you trust them, and never risk money you can't afford to lose.

## How signals work

Each symbol is scored on daily candles from Yahoo Finance. Each check adds −1, 0 or +1:

| Check | Bullish (+1) | Bearish (−1) |
|---|---|---|
| Long-term trend | Close above 200-day SMA | Close below 200-day SMA |
| Golden/death cross | 50-day SMA above 200-day | 50-day SMA below 200-day |
| MACD (12/26/9) | MACD above signal line | MACD below signal line |
| RSI (14) | Below 30 (oversold) | Above 70 (overbought) |

The score runs from −4 to +4. A score of **≥ +2 means BUY**, **≤ −2 means SELL**, and anything else is HOLD.

You get an alert only when a symbol **changes** into BUY or SELL, so the same signal isn't repeated every day. The last signal for each symbol is saved in `state.json`, which the workflow commits back to the repository. Today's unfinished candle is ignored, so signals don't flicker during the day.

## Setup (about 5 minutes)

1. **Create a Telegram bot.** In Telegram, message **@BotFather** and send `/newbot`. It replies with a **bot token**.
2. **Get your chat ID.** Send any message to your new bot, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser. Copy the value of `"chat":{"id": ...}`.
3. **Add the repository secrets.** On GitHub, go to Settings → Secrets and variables → Actions and add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. **Choose your symbols** by editing `config.yaml`. For example:
   - Stocks: `AAPL`
   - Crypto: `BTC-USD`
   - Forex: `EURUSD=X`
5. **Test it.** Go to Actions → *Trading signals* → **Run workflow**. You should receive a full summary in Telegram. After that, it runs automatically every day at 05:37 UTC and sends a daily summary, plus a "Time to BUY / SELL" alert whenever a signal changes.

## Backtest (does this actually work?)

Go to Actions → **Backtest** → **Run workflow**. It replays the BUY/SELL rules over the last 10 years (or 3, 5, 20 or max) of your watchlist and sends you the results in Telegram. For each symbol you get:
- what $1,000 would have become by following the signals, compared with buying and holding
- the worst drop along the way
- the share of trades that made money

## Run locally

```bash
pip install -r requirements.txt
python -m trading_signals.main --report     # prints to the terminal (or sends to Telegram if the env vars are set)
python -m trading_signals.backtest AAPL BTC-USD --period 10y
pytest
```

The backtest buys on BUY signals, sells on SELL signals, and charges a 0.1% fee per trade. It compares the result with simply buying and holding, including total return and maximum drawdown. You can tune the thresholds and periods under `strategy:` in `config.yaml`.
