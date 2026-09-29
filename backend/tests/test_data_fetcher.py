import pandas as pd
import pytest

from app import data_fetcher


class FakeTicker:
    def __init__(self, closes, volumes):
        self._closes = closes
        self._volumes = volumes

    def history(self, period="1y"):
        return pd.DataFrame({"Close": self._closes, "Volume": self._volumes})


class AlwaysFailsTicker:
    def history(self, period="1y"):
        raise RuntimeError("network error")


def test_fetch_history_returns_price_history(monkeypatch):
    monkeypatch.setattr(
        data_fetcher.yf, "Ticker", lambda t: FakeTicker([10.0, 11.0, 12.0], [100, 200, 300])
    )
    result = data_fetcher.fetch_history("AAPL")
    assert result.ticker == "AAPL"
    assert result.closes == [10.0, 11.0, 12.0]
    assert result.volumes == [100, 200, 300]


def test_fetch_history_retries_then_gives_up(monkeypatch):
    monkeypatch.setattr(data_fetcher.yf, "Ticker", lambda t: AlwaysFailsTicker())
    monkeypatch.setattr(data_fetcher.time, "sleep", lambda s: None)
    result = data_fetcher.fetch_history("AAPL", retries=2)
    assert result is None


def test_fetch_current_price_and_change(monkeypatch):
    monkeypatch.setattr(
        data_fetcher.yf, "Ticker", lambda t: FakeTicker([100.0, 110.0], [100, 200])
    )
    price, pct_change = data_fetcher.fetch_current_price_and_change("AAPL")
    assert price == 110.0
    assert round(pct_change, 2) == 10.0


def test_fetch_history_drops_nan_close_rows(monkeypatch):
    monkeypatch.setattr(
        data_fetcher.yf,
        "Ticker",
        lambda t: FakeTicker([10.0, float("nan"), 12.0], [100, 200, 300]),
    )
    result = data_fetcher.fetch_history("AAPL")
    assert result.closes == [10.0, 12.0]
    assert result.volumes == [100, 300]


def test_fetch_history_returns_none_when_all_closes_are_nan(monkeypatch):
    monkeypatch.setattr(
        data_fetcher.yf,
        "Ticker",
        lambda t: FakeTicker([float("nan"), float("nan")], [100, 200]),
    )
    result = data_fetcher.fetch_history("AAPL")
    assert result is None


def test_fetch_current_price_and_change_no_data(monkeypatch):
    monkeypatch.setattr(data_fetcher.yf, "Ticker", lambda t: AlwaysFailsTicker())
    monkeypatch.setattr(data_fetcher.time, "sleep", lambda s: None)
    price, pct_change = data_fetcher.fetch_current_price_and_change("AAPL")
    assert price is None
    assert pct_change is None
