import pandas as pd

from app import universe
from app.db import get_connection, init_db

# fetch_sp500_tickers/fetch_nasdaq100_tickers now fetch the page HTML themselves
# (via universe._fetch_html, using a custom User-Agent so Wikipedia doesn't 403
# them) and pass the text to pd.read_html(io.StringIO(html)). Tests fake both
# steps: _fetch_html returns a marker string identifying which page was
# requested, and the fake pd.read_html inspects that marker to decide which
# fake table to return, so the "which URL was fetched" assertion still holds.


def _fake_fetch_html(url):
    if "S%26P_500" in url:
        return "<html>sp500-page</html>"
    if "NASDAQ-100" in url:
        return "<html>nasdaq100-page</html>"
    raise AssertionError(f"unexpected url: {url}")


def _fake_read_html(html_io):
    content = html_io.getvalue()
    if "sp500-page" in content:
        return [pd.DataFrame({"Symbol": ["AAPL", "MSFT", "BRK.B"]})]
    return [pd.DataFrame({"Ticker": ["GOOGL", "AMZN"]})]


def test_refresh_universe_writes_tickers(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    monkeypatch.setattr(universe, "_fetch_html", _fake_fetch_html)
    monkeypatch.setattr(universe.pd, "read_html", _fake_read_html)

    count = universe.refresh_universe(db_path)

    assert count == 5  # AAPL, MSFT, BRK-B, GOOGL, AMZN
    tickers = set(universe.get_universe_tickers(db_path))
    assert tickers == {"AAPL", "MSFT", "BRK-B", "GOOGL", "AMZN"}


def test_refresh_universe_replaces_previous_list(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    monkeypatch.setattr(universe, "_fetch_html", _fake_fetch_html)
    monkeypatch.setattr(universe.pd, "read_html", _fake_read_html)
    universe.refresh_universe(db_path)

    def _fake_read_html_v2(html_io):
        content = html_io.getvalue()
        if "sp500-page" in content:
            return [pd.DataFrame({"Symbol": ["TSLA"]})]
        return [pd.DataFrame({"Ticker": ["NVDA"]})]

    monkeypatch.setattr(universe.pd, "read_html", _fake_read_html_v2)
    universe.refresh_universe(db_path)

    tickers = set(universe.get_universe_tickers(db_path))
    assert tickers == {"TSLA", "NVDA"}


def test_refresh_universe_failure_keeps_previous_list(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    monkeypatch.setattr(universe, "_fetch_html", _fake_fetch_html)
    monkeypatch.setattr(universe.pd, "read_html", _fake_read_html)
    universe.refresh_universe(db_path)

    def _boom(url):
        raise RuntimeError("network down")

    monkeypatch.setattr(universe, "_fetch_html", _boom)

    try:
        universe.refresh_universe(db_path)
        raised = False
    except RuntimeError:
        raised = True

    assert raised is True
    # ensure the DB was never touched by the failed call
    tickers = set(universe.get_universe_tickers(db_path))
    assert tickers == {"AAPL", "MSFT", "BRK-B", "GOOGL", "AMZN"}


def test_fetch_sp500_tickers_uses_custom_user_agent(monkeypatch):
    captured_requests = []

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"<table><tr><th>Symbol</th></tr><tr><td>AAPL</td></tr></table>"

    def _fake_urlopen(request):
        captured_requests.append(request)
        return _FakeResponse()

    monkeypatch.setattr(universe.urllib.request, "urlopen", _fake_urlopen)

    tickers = universe.fetch_sp500_tickers()

    assert tickers == ["AAPL"]
    assert len(captured_requests) == 1
    assert captured_requests[0].get_header("User-agent") == universe._USER_AGENT
