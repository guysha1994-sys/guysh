from __future__ import annotations


def sma(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def pct_from_52w_high(closes: list[float]) -> float | None:
    if not closes:
        return None
    high = max(closes)
    if high == 0:
        return None
    current = closes[-1]
    return (current - high) / high * 100


def relative_strength(
    stock_closes: list[float], benchmark_closes: list[float]
) -> float | None:
    if len(stock_closes) < 2 or len(benchmark_closes) < 2:
        return None
    if stock_closes[0] == 0 or benchmark_closes[0] == 0:
        return None
    stock_return = (stock_closes[-1] - stock_closes[0]) / stock_closes[0]
    benchmark_return = (benchmark_closes[-1] - benchmark_closes[0]) / benchmark_closes[0]
    return (stock_return - benchmark_return) * 100


def avg_dollar_volume(closes: list[float], volumes: list[float]) -> float:
    if not closes or not volumes:
        return 0.0
    n = min(len(closes), len(volumes))
    total = sum(closes[-i - 1] * volumes[-i - 1] for i in range(n))
    return total / n
