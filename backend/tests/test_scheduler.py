from datetime import date
from types import SimpleNamespace

import pandas as pd
from apscheduler.triggers.cron import CronTrigger

import app.scheduler as scheduler_module
import app.screener as screener_module
import app.universe as universe_module
from app.config import Settings
from app.data_fetcher import PriceHistory
from app.db import get_connection, init_db


def _fake_fetch_html(url):
    if "S%26P_500" in url:
        return "<html>sp500-page</html>"
    return "<html>nasdaq100-page</html>"


def _fake_read_html(html_io):
    content = html_io.getvalue()
    if "sp500-page" in content:
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

    monkeypatch.setattr(universe_module, "_fetch_html", _fake_fetch_html)
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


class _FakeBackgroundScheduler:
    """Stand-in for APScheduler's BackgroundScheduler that records the job/trigger
    passed to add_job without starting any real thread, so we can assert on
    exactly what start_scheduler() builds."""

    def __init__(self, timezone=None):
        self.timezone = timezone
        self._jobs = {}

    def add_job(self, func, trigger, args=None, id=None):
        self._jobs[id] = SimpleNamespace(func=func, trigger=trigger, args=args)

    def get_job(self, job_id):
        return self._jobs.get(job_id)

    def start(self):
        pass

    def shutdown(self, wait=True):
        pass


def test_start_scheduler_pins_daily_job_to_america_new_york(tmp_path, monkeypatch):
    settings = Settings(db_path=str(tmp_path / "test.db"), session_secret="s", login_password="p")

    fake_scheduler = _FakeBackgroundScheduler()
    monkeypatch.setattr(scheduler_module, "_scheduler", None)
    monkeypatch.setattr(
        scheduler_module, "BackgroundScheduler", lambda timezone=None: fake_scheduler
    )

    try:
        scheduler_module.start_scheduler(settings)

        job = fake_scheduler.get_job("daily_screener")
        assert job is not None
        # BackgroundScheduler(timezone=...) only sets a default for triggers built
        # from a string alias; it does NOT propagate to a CronTrigger object we
        # construct ourselves, so the trigger itself must carry the timezone.
        assert str(job.trigger.timezone) == "America/New_York"
    finally:
        monkeypatch.setattr(scheduler_module, "_scheduler", None)


def test_cron_trigger_with_explicit_timezone_is_pinned_to_america_new_york():
    trigger = CronTrigger(hour=16, minute=30, day_of_week="mon-fri", timezone="America/New_York")
    assert str(trigger.timezone) == "America/New_York"


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
