import pandas as pd

from app import universe
from app.db import get_connection, init_db


def _fake_read_html(url):
    if "S%26P_500" in url:
        return [pd.DataFrame({"Symbol": ["AAPL", "MSFT", "BRK.B"]})]
    return [pd.DataFrame({"Ticker": ["GOOGL", "AMZN"]})]


def test_refresh_universe_writes_tickers(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    monkeypatch.setattr(universe.pd, "read_html", _fake_read_html)

    count = universe.refresh_universe(db_path)

    assert count == 5  # AAPL, MSFT, BRK-B, GOOGL, AMZN
    tickers = set(universe.get_universe_tickers(db_path))
    assert tickers == {"AAPL", "MSFT", "BRK-B", "GOOGL", "AMZN"}


def test_refresh_universe_replaces_previous_list(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    monkeypatch.setattr(universe.pd, "read_html", _fake_read_html)
    universe.refresh_universe(db_path)

    monkeypatch.setattr(
        universe.pd,
        "read_html",
        lambda url: [pd.DataFrame({"Symbol": ["TSLA"]})]
        if "S%26P_500" in url
        else [pd.DataFrame({"Ticker": ["NVDA"]})],
    )
    universe.refresh_universe(db_path)

    tickers = set(universe.get_universe_tickers(db_path))
    assert tickers == {"TSLA", "NVDA"}


def test_refresh_universe_failure_keeps_previous_list(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    monkeypatch.setattr(universe.pd, "read_html", _fake_read_html)
    universe.refresh_universe(db_path)

    def _boom(url):
        raise RuntimeError("network down")

    monkeypatch.setattr(universe.pd, "read_html", _boom)

    try:
        universe.refresh_universe(db_path)
        raised = False
    except RuntimeError:
        raised = True

    assert raised is True
    # ensure the DB was never touched by the failed call
    tickers = set(universe.get_universe_tickers(db_path))
    assert tickers == {"AAPL", "MSFT", "BRK-B", "GOOGL", "AMZN"}
