import json

from app.data_fetcher import PriceHistory
from app.db import get_connection, init_db
from app.screener import (
    ScreenerConfig,
    evaluate_ticker,
    run_screener,
    save_screener_results,
)
from datetime import date


def _uptrend_closes(n=260, start=50.0, daily_gain=0.15):
    closes = []
    price = start
    for _ in range(n):
        closes.append(price)
        price += daily_gain
    return closes


def test_evaluate_ticker_passes_for_strong_uptrend():
    closes = _uptrend_closes()
    volumes = [1_000_000] * len(closes)
    history = PriceHistory(ticker="AAPL", closes=closes, volumes=volumes)
    benchmark = PriceHistory(
        ticker="^GSPC", closes=_uptrend_closes(daily_gain=0.02), volumes=[0] * 260
    )

    result = evaluate_ticker(history, benchmark, ScreenerConfig())

    assert result is not None
    assert result.ticker == "AAPL"
    assert "relative_strength" in result.metrics


def test_evaluate_ticker_rejects_downtrend():
    closes = list(reversed(_uptrend_closes()))  # יורד עם הזמן
    volumes = [1_000_000] * len(closes)
    history = PriceHistory(ticker="XYZ", closes=closes, volumes=volumes)
    benchmark = PriceHistory(
        ticker="^GSPC", closes=_uptrend_closes(daily_gain=0.02), volumes=[0] * 260
    )

    result = evaluate_ticker(history, benchmark, ScreenerConfig())

    assert result is None


def test_evaluate_ticker_rejects_low_liquidity():
    closes = _uptrend_closes()
    volumes = [10] * len(closes)  # מחזור זעיר
    history = PriceHistory(ticker="ILLIQUID", closes=closes, volumes=volumes)
    benchmark = PriceHistory(
        ticker="^GSPC", closes=_uptrend_closes(daily_gain=0.02), volumes=[0] * 260
    )

    result = evaluate_ticker(history, benchmark, ScreenerConfig())

    assert result is None


def test_run_screener_ranks_and_limits_results(monkeypatch):
    import app.screener as screener_module

    strong = PriceHistory("STRONG", _uptrend_closes(daily_gain=0.30), [1_000_000] * 260)
    weak = PriceHistory("WEAK", _uptrend_closes(daily_gain=0.05), [1_000_000] * 260)
    benchmark = PriceHistory("^GSPC", _uptrend_closes(daily_gain=0.02), [0] * 260)

    histories = {"STRONG": strong, "WEAK": weak, "^GSPC": benchmark}
    monkeypatch.setattr(
        screener_module, "fetch_history", lambda ticker, period="1y": histories.get(ticker)
    )

    results = run_screener(["STRONG", "WEAK"], top_n=1)

    assert len(results) == 1
    assert results[0].ticker == "STRONG"


def test_save_screener_results_persists_and_replaces(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    from app.screener import ScreenerResult

    results = [ScreenerResult(ticker="AAPL", score=12.5, metrics={"pct_from_52w_high": -1.0})]
    save_screener_results(db_path, results, date(2026, 9, 29))

    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM screener_results").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAPL"
    assert json.loads(rows[0]["metrics"])["pct_from_52w_high"] == -1.0
