# backend/tests/test_integration_flow.py
from pathlib import Path

import pytest

import app.routers.indices as indices_router
import app.routers.portfolio as portfolio_router
import app.routers.recommendations as recommendations_router
from app.db import get_connection
from app.screener import ScreenerResult, save_screener_results
from datetime import date


def test_full_flow_login_buy_recommend_indices(client, settings, monkeypatch):
    monkeypatch.setattr(
        portfolio_router, "fetch_current_price_and_change", lambda t: (120.0, 1.0)
    )
    monkeypatch.setattr(
        recommendations_router, "fetch_current_price_and_change", lambda t: (200.0, -0.5)
    )
    monkeypatch.setattr(
        indices_router, "fetch_current_price_and_change", lambda t: (450.0, 0.3)
    )

    # לא מחוברים עדיין
    assert client.get("/api/portfolio").status_code == 401

    # התחברות
    login_resp = client.post("/api/auth/login", json={"password": "test-password"})
    assert login_resp.status_code == 200

    # קנייה
    buy_resp = client.post(
        "/api/portfolio",
        json={"ticker": "AAPL", "entry_price": 100.0, "quantity": 10, "stop_loss": 90.0},
    )
    assert buy_resp.status_code == 200

    # תיק מציג את הפוזיציה
    portfolio_resp = client.get("/api/portfolio")
    assert len(portfolio_resp.json()) == 1

    # מכינים נתוני screener ובודקים את מסך ההמלצות
    save_screener_results(
        settings.db_path,
        [ScreenerResult(ticker="MSFT", score=15.0, metrics={"pct_from_52w_high": -2.0})],
        date.today(),
    )
    recs_resp = client.get("/api/recommendations")
    assert recs_resp.json()["results"][0]["ticker"] == "MSFT"

    # מוסיפים מדד ובודקים את מסך המדדים
    client.post("/api/indices", json={"symbol": "SOXX", "display_name": "SOXX"})
    indices_resp = client.get("/api/indices")
    assert indices_resp.json()[0]["symbol"] == "SOXX"

    # מוכרים את הפוזיציה
    position_id = portfolio_resp.json()[0]["id"]
    sell_resp = client.post(f"/api/portfolio/{position_id}/sell")
    assert sell_resp.status_code == 200
    assert client.get("/api/portfolio").json() == []


def test_create_app_starts_scheduler_by_default(settings, monkeypatch):
    import app.main as main_module

    started = {}
    monkeypatch.setattr(
        main_module, "start_scheduler", lambda s: started.setdefault("called", True)
    )

    main_module.create_app(settings)

    assert started.get("called") is True


def test_spa_client_routes_fall_back_to_index_html(client):
    # This exercises the real `frontend/dist` build mounted by create_app (via the
    # `client` fixture), not a synthetic stand-in — if the frontend hasn't been
    # built, the `if frontend_dist.exists():` branch in main.py never registers the
    # StaticFiles mount or the SPA fallback handler, so there'd be nothing to test.
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if not frontend_dist.exists():
        pytest.skip("frontend/dist is not built; SPA fallback mount is inactive")

    # A client-side route with no matching static file must fall back to
    # index.html (200, HTML), not the raw StaticFiles 404.
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert resp.content != b'{"detail":"Not Found"}'

    # A genuinely missing API route must still be a plain JSON 404, unaffected
    # by the SPA fallback.
    api_resp = client.get("/api/definitely-not-a-real-route")
    assert api_resp.status_code == 404
    assert api_resp.json() == {"detail": "Not Found"}


def test_create_app_skips_scheduler_when_disabled(settings, monkeypatch):
    import app.main as main_module

    started = {}
    monkeypatch.setattr(
        main_module, "start_scheduler", lambda s: started.setdefault("called", True)
    )

    main_module.create_app(settings, start_scheduler_job=False)

    assert "called" not in started
