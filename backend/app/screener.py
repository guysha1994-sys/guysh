from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from app.data_fetcher import PriceHistory, fetch_history
from app.db import get_connection
from app.indicators import avg_dollar_volume, pct_from_52w_high, relative_strength, sma


@dataclass(frozen=True)
class ScreenerConfig:
    sma_short_window: int = 50
    sma_long_window: int = 200
    max_pct_below_52w_high: float = 15.0
    min_avg_dollar_volume: float = 5_000_000.0
    relative_strength_weeks: int = 12


@dataclass
class ScreenerResult:
    ticker: str
    score: float
    metrics: dict


def evaluate_ticker(
    history: PriceHistory,
    benchmark_history: PriceHistory,
    config: ScreenerConfig,
) -> ScreenerResult | None:
    closes = history.closes
    if len(closes) < config.sma_long_window:
        return None

    sma_short = sma(closes, config.sma_short_window)
    sma_long = sma(closes, config.sma_long_window)
    if sma_short is None or sma_long is None:
        return None
    if not (closes[-1] > sma_short > sma_long):
        return None

    pct_high = pct_from_52w_high(closes)
    if pct_high is None or pct_high < -config.max_pct_below_52w_high:
        return None

    dollar_volume = avg_dollar_volume(closes, history.volumes)
    if dollar_volume < config.min_avg_dollar_volume:
        return None

    weeks_of_days = config.relative_strength_weeks * 5
    rel_strength = relative_strength(
        closes[-weeks_of_days:], benchmark_history.closes[-weeks_of_days:]
    )
    if rel_strength is None or rel_strength <= 0:
        return None

    score = rel_strength + (100 + pct_high)
    return ScreenerResult(
        ticker=history.ticker,
        score=score,
        metrics={
            "pct_from_52w_high": pct_high,
            "relative_strength": rel_strength,
            "avg_dollar_volume": dollar_volume,
        },
    )


def run_screener(
    tickers: list[str],
    benchmark_ticker: str = "^GSPC",
    config: ScreenerConfig | None = None,
    top_n: int = 20,
) -> list[ScreenerResult]:
    config = config or ScreenerConfig()
    benchmark_history = fetch_history(benchmark_ticker, period="1y")
    if benchmark_history is None:
        return []

    results: list[ScreenerResult] = []
    for ticker in tickers:
        history = fetch_history(ticker, period="1y")
        if history is None:
            continue
        result = evaluate_ticker(history, benchmark_history, config)
        if result is not None:
            results.append(result)

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]


def save_screener_results(db_path: str, results: list[ScreenerResult], run_date: date) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM screener_results WHERE run_date = ?", (run_date.isoformat(),))
        conn.executemany(
            "INSERT INTO screener_results (run_date, ticker, score, metrics) VALUES (?, ?, ?, ?)",
            [
                (run_date.isoformat(), r.ticker, r.score, json.dumps(r.metrics))
                for r in results
            ],
        )
        conn.commit()
    finally:
        conn.close()
