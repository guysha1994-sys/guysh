import app.routers.indices as indices_router


def _login(client):
    client.post("/api/auth/login", json={"password": "test-password"})


def test_add_list_and_remove_index(client, monkeypatch):
    monkeypatch.setattr(
        indices_router, "fetch_current_price_and_change", lambda t: (450.0, -0.8)
    )
    _login(client)

    add_resp = client.post("/api/indices", json={"symbol": "soxx", "display_name": "SOXX"})
    assert add_resp.status_code == 200

    list_resp = client.get("/api/indices")
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body == [
        {"symbol": "SOXX", "display_name": "SOXX", "current_price": 450.0, "pct_change": -0.8}
    ]

    remove_resp = client.delete("/api/indices/SOXX")
    assert remove_resp.status_code == 200

    list_resp_after = client.get("/api/indices")
    assert list_resp_after.json() == []


def test_indices_preserve_insertion_order(client, monkeypatch):
    monkeypatch.setattr(
        indices_router, "fetch_current_price_and_change", lambda t: (100.0, 0.0)
    )
    _login(client)

    client.post("/api/indices", json={"symbol": "QQQ", "display_name": "Nasdaq 100"})
    client.post("/api/indices", json={"symbol": "SPY", "display_name": "S&P 500"})

    resp = client.get("/api/indices")
    symbols = [row["symbol"] for row in resp.json()]
    assert symbols == ["QQQ", "SPY"]
