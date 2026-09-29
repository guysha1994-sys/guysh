from __future__ import annotations

import io
import urllib.request

import pandas as pd

from app.db import get_connection

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies"

# Wikipedia blocks the default `Python-urllib` User-Agent (pandas' urllib default)
# with a 403, so we fetch the page ourselves with a browser-like UA and hand the
# HTML text to pandas instead of letting pd.read_html fetch the URL itself.
_USER_AGENT = (
    "Mozilla/5.0 (compatible; StockerBot/1.0; +https://github.com/)"
)


def _fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8")


def fetch_sp500_tickers() -> list[str]:
    html = _fetch_html(SP500_URL)
    tables = pd.read_html(io.StringIO(html))
    df = tables[0]
    return [str(t).replace(".", "-") for t in df["Symbol"].tolist()]


def fetch_nasdaq100_tickers() -> list[str]:
    html = _fetch_html(NASDAQ100_URL)
    tables = pd.read_html(io.StringIO(html))
    for table in tables:
        if "Ticker" in table.columns:
            return [str(t).replace(".", "-") for t in table["Ticker"].tolist()]
    raise ValueError("Could not find Nasdaq-100 ticker table")


def refresh_universe(db_path: str) -> int:
    # שולפים קודם — אם אחת הקריאות נכשלת, ה-DB לא נגע כלל ונשארת
    # הרשימה השמורה האחרונה (דרישת טיפול-בשגיאות מה-spec).
    sp500 = fetch_sp500_tickers()
    nasdaq100 = fetch_nasdaq100_tickers()

    rows = [(t, "sp500") for t in sp500] + [(t, "nasdaq100") for t in nasdaq100]

    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM universe_tickers")
        conn.executemany(
            "INSERT OR IGNORE INTO universe_tickers (ticker, index_name) VALUES (?, ?)",
            rows,
        )
        conn.commit()
        return len({t for t, _ in rows})
    finally:
        conn.close()


def get_universe_tickers(db_path: str) -> list[str]:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT DISTINCT ticker FROM universe_tickers")
        return [row["ticker"] for row in cursor.fetchall()]
    finally:
        conn.close()
