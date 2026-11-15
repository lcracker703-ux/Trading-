"""Market data from Yahoo Finance (stocks, ETFs, crypto e.g. BTC-USD, forex e.g. EURUSD=X)."""
from datetime import datetime, timezone

import pandas as pd


def fetch_daily(symbol: str, period: str = "2y") -> pd.DataFrame:
    import yfinance as yf

    df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
    if df.empty:
        raise ValueError(f"No data returned for {symbol}")
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
    return drop_incomplete_bar(df)


def drop_incomplete_bar(df: pd.DataFrame, now: datetime | None = None) -> pd.DataFrame:
    """Drop today's still-forming candle so signals don't flip-flop intraday."""
    now = now or datetime.now(timezone.utc)
    last = pd.Timestamp(df.index[-1])
    last_date = last.tz_convert("UTC").date() if last.tzinfo else last.date()
    if last_date >= now.date():
        return df.iloc[:-1]
    return df
