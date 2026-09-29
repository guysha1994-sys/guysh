# backend/tests/test_auth.py
def test_protected_route_rejects_without_login(client):
    resp = client.get("/api/portfolio")
    assert resp.status_code == 401


def test_login_with_correct_password_allows_access(client):
    login_resp = client.post("/api/auth/login", json={"password": "test-password"})
    assert login_resp.status_code == 200
    assert login_resp.json() == {"ok": True}

    portfolio_resp = client.get("/api/portfolio")
    assert portfolio_resp.status_code == 200


def test_login_with_wrong_password_rejected(client):
    resp = client.post("/api/auth/login", json={"password": "wrong"})
    assert resp.status_code == 401


def test_logout_clears_session(client):
    client.post("/api/auth/login", json={"password": "test-password"})
    client.post("/api/auth/logout")
    resp = client.get("/api/portfolio")
    assert resp.status_code == 401
