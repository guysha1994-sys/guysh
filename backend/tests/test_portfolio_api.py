import app.routers.portfolio as portfolio_router


def _login(client):
    client.post("/api/auth/login", json={"password": "test-password"})


def test_buy_then_list_shows_position(client, monkeypatch):
    monkeypatch.setattr(
        portfolio_router, "fetch_current_price_and_change", lambda t: (120.0, 2.5)
    )
    _login(client)

    buy_resp = client.post(
        "/api/portfolio", json={"ticker": "aapl", "entry_price": 100.0, "stop_loss": 90.0}
    )
    assert buy_resp.status_code == 200
    position_id = buy_resp.json()["id"]

    list_resp = client.get("/api/portfolio")
    assert list_resp.status_code == 200
    positions = list_resp.json()
    assert len(positions) == 1
    assert positions[0]["ticker"] == "AAPL"
    assert positions[0]["current_price"] == 120.0
    assert positions[0]["pct_change"] == 2.5
    assert round(positions[0]["pnl_pct"], 2) == 20.0
    assert positions[0]["id"] == position_id


def test_sell_removes_position_from_open_list(client, monkeypatch):
    monkeypatch.setattr(
        portfolio_router, "fetch_current_price_and_change", lambda t: (120.0, 2.5)
    )
    _login(client)

    buy_resp = client.post(
        "/api/portfolio", json={"ticker": "AAPL", "entry_price": 100.0, "stop_loss": 90.0}
    )
    position_id = buy_resp.json()["id"]

    sell_resp = client.post(f"/api/portfolio/{position_id}/sell")
    assert sell_resp.status_code == 200

    list_resp = client.get("/api/portfolio")
    assert list_resp.json() == []


def test_sell_unknown_position_returns_404(client):
    _login(client)
    resp = client.post("/api/portfolio/999/sell")
    assert resp.status_code == 404
