from __future__ import annotations

import time
from dataclasses import dataclass

import yfinance as yf


@dataclass
class PriceHistory:
    ticker: str
    closes: list[float]
    volumes: list[float]


def fetch_history(
    ticker: str, period: str = "1y", retries: int = 3, backoff_seconds: float = 1.0
) -> PriceHistory | None:
    for attempt in range(retries):
        try:
            data = yf.Ticker(ticker).history(period=period)
            if data.empty:
                return None
            return PriceHistory(
                ticker=ticker,
                closes=data["Close"].tolist(),
                volumes=data["Volume"].tolist(),
            )
        except Exception:
            time.sleep(backoff_seconds * (attempt + 1))
    return None


def fetch_current_price_and_change(ticker: str) -> tuple[float | None, float | None]:
    history = fetch_history(ticker, period="5d", retries=2)
    if history is None or not history.closes:
        return None, None
    current = history.closes[-1]
    if len(history.closes) < 2:
        return current, None
    previous = history.closes[-2]
    if previous == 0:
        return current, None
    pct_change = (current - previous) / previous * 100
    return current, pct_change
