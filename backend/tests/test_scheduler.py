from datetime import date

import pandas as pd

import app.scheduler as scheduler_module
import app.screener as screener_module
import app.universe as universe_module
from app.config import Settings
from app.data_fetcher import PriceHistory
from app.db import get_connection, init_db


def _fake_read_html(url):
    if "S%26P_500" in url:
        return [pd.DataFrame({"Symbol": ["AAPL"]})]
    return [pd.DataFrame({"Ticker": ["GOOGL"]})]


def _uptrend_closes(n=260, start=50.0, daily_gain=0.15):
    closes = []
    price = start
    for _ in range(n):
        closes.append(price)
        price += daily_gain
    return closes


def test_run_daily_job_writes_screener_results(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    settings = Settings(db_path=db_path, session_secret="s", login_password="p")

    monkeypatch.setattr(universe_module.pd, "read_html", _fake_read_html)

    histories = {
        "AAPL": PriceHistory("AAPL", _uptrend_closes(daily_gain=0.30), [1_000_000] * 260),
        "GOOGL": PriceHistory("GOOGL", _uptrend_closes(daily_gain=0.30), [1_000_000] * 260),
        "^GSPC": PriceHistory("^GSPC", _uptrend_closes(daily_gain=0.02), [0] * 260),
    }
    monkeypatch.setattr(
        screener_module, "fetch_history", lambda ticker, period="1y": histories.get(ticker)
    )

    scheduler_module.run_daily_job(settings)

    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM screener_results WHERE run_date = ?", (date.today().isoformat(),)
    ).fetchall()
    conn.close()

    tickers = {row["ticker"] for row in rows}
    assert tickers == {"AAPL", "GOOGL"}


def test_run_daily_job_survives_universe_refresh_failure(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    settings = Settings(db_path=db_path, session_secret="s", login_password="p")

    # אין טיקרים ב-universe_tickers ורענון נכשל — הריצה לא אמורה לזרוק
    def _boom():
        raise RuntimeError("network down")

    monkeypatch.setattr(scheduler_module, "refresh_universe", lambda db_path: _boom())

    scheduler_module.run_daily_job(settings)  # לא אמור לזרוק חריגה

    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM screener_results").fetchall()
    conn.close()
    assert rows == []
