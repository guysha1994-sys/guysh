from datetime import date

import app.routers.recommendations as recommendations_router
from app.db import get_connection
from app.screener import ScreenerResult, save_screener_results


def _login(client):
    client.post("/api/auth/login", json={"password": "test-password"})


def test_recommendations_empty_when_no_runs_yet(client):
    _login(client)
    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    assert resp.json() == {"run_date": None, "results": []}


def test_recommendations_returns_latest_run_sorted_by_score(client, settings, monkeypatch):
    results = [
        ScreenerResult(ticker="AAPL", score=10.0, metrics={"pct_from_52w_high": -1.0}),
        ScreenerResult(ticker="MSFT", score=20.0, metrics={"pct_from_52w_high": -0.5}),
    ]
    save_screener_results(settings.db_path, results, date.today())

    monkeypatch.setattr(
        recommendations_router, "fetch_current_price_and_change", lambda t: (150.0, 1.2)
    )
    _login(client)

    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_date"] == date.today().isoformat()
    tickers_in_order = [r["ticker"] for r in body["results"]]
    assert tickers_in_order == ["MSFT", "AAPL"]
    assert body["results"][0]["current_price"] == 150.0
    assert body["results"][0]["pct_change"] == 1.2
    assert body["results"][0]["pct_from_52w_high"] == -0.5
