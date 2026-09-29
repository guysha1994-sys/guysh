# Stocker Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** בניית ה-backend (FastAPI + SQLite) המלא לאפליקציית ההשקעות: data
fetcher, אינדיקטורים, סקרינר, ריצת EOD מתוזמנת, אימות בסיסמה, ו-API
מלא לתיק/המלצות/מדדים. בסוף הפלאן יש שרת שאפשר להריץ מקומית ולבדוק
עם curl/pytest — בלי frontend עדיין.

**Architecture:** Python 3.9+ (local dev), FastAPI מעל Starlette (session cookies
מובנים), SQLite גולמי (בלי ORM) דרך מודול `db.py` אחד, `yfinance` בתור
מקור הנתונים היחיד, `APScheduler` לריצת ה-EOD היומית. כל מודול לוגי
(indicators/screener/data_fetcher/universe/portfolio) הוא קובץ נפרד עם
פונקציות טהורות ככל האפשר, נבדק ב-unit test בלי תלות ברשת.

**Tech Stack:** FastAPI, Uvicorn, Starlette SessionMiddleware
(itsdangerous), yfinance, pandas + lxml (ל-`pd.read_html`),
APScheduler, sqlite3 (built-in), pytest, httpx (ל-TestClient).

**Spec:** [docs/superpowers/specs/2026-09-29-stock-recommendation-webapp-design.md](../specs/2026-09-29-stock-recommendation-webapp-design.md)

## Global Constraints

- Python 3.9+ לפיתוח מקומי (מכונת הפיתוח הזמינה כרגע נושאת רק 3.9.6,
  בלי pyenv/Homebrew להתקין גרסה חדשה יותר) — כל מודול פותח עם
  `from __future__ import annotations` כדי ש-`X | None` (PEP604) יעבוד
  גם על 3.9. תמונת ה-Docker (Task 13) עדיין `python:3.11-slim` — זה לא
  תלוי בגרסת הפייתון של מכונת הפיתוח. בלי ORM — גישה ל-SQLite דרך
  `sqlite3` גולמי בלבד.
- אימות: סיסמה בודדת מתוך `STOCKER_LOGIN_PASSWORD` (env var), מושווית
  עם `hmac.compare_digest`. בלי טבלת משתמשים, בלי הרשמה, בלי ריבוי
  משתמשים (מחוץ לתחום לפי ה-spec).
- ספי/פרמטרי הסקרינר חייבים לשבת ב-`ScreenerConfig` dataclass
  (`app/screener.py`) — אף פעם לא hardcoded בתוך הלוגיקה עצמה.
  יוניברס הסריקה = S&P 500 ∪ Nasdaq-100 (נשלף מטבלאות ויקיפדיה).
- כל קריאה חיצונית (yfinance, `pd.read_html`) חייבת retry/skip — כשלון
  בטיקר בודד לא יפיל ריצת screener שלמה; כשלון ברענון היוניברס משאיר
  את הרשימה השמורה האחרונה (בלי לזרוק שגיאה מתוך ה-job המתוזמן).
- אין חיבור ברוקר אמיתי, אין התראות push/טלגרם — מחוץ לתחום לפי ה-spec.
- הפלאן הזה מכסה **backend בלבד**. ה-React frontend + PWA + פריסה
  יהיו פלאן נפרד שייכתב אחרי שה-backend הזה יעבוד ויעבור בדיקות.
- כל בדיקה רצה מתוך תיקיית `backend/` עם `pytest tests/ -v`.

---

### Task 1: Backend scaffold + health endpoint

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_health.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: `Settings` dataclass (`app/config.py`) עם שדות `db_path: str`,
  `session_secret: str`, `login_password: str`, ו-classmethod
  `Settings.from_env() -> Settings`.
- Produces: `create_app(settings: Settings | None = None) -> FastAPI`
  (`app/main.py`) — משמש בכל שאר המשימות להרכבת ה-app.
- Produces: `pytest` fixtures `settings` ו-`client` ב-`tests/conftest.py`,
  בשימוש בכל קבצי הטסטים הבאים.

- [ ] **Step 1: יצירת מבנה הפרויקט ו-requirements**

```bash
mkdir -p backend/app/routers backend/tests
```

`backend/requirements.txt`:
```
fastapi>=0.110
uvicorn[standard]>=0.29
itsdangerous>=2.1
yfinance>=0.2.40
pandas>=2.2
lxml>=5.0
apscheduler>=3.10
pytest>=8.0
httpx>=0.27
```

`backend/pytest.ini`:
```ini
[pytest]
pythonpath = .
```

`.gitignore` (בשורש הריפו):
```
__pycache__/
*.pyc
*.db
.venv/
node_modules/
dist/
```

`backend/app/__init__.py`: קובץ ריק.

- [ ] **Step 2: התקנת תלויות**

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

- [ ] **Step 3: כתיבת `config.py`**

```python
# backend/app/config.py
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str
    session_secret: str
    login_password: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=os.environ.get("STOCKER_DB_PATH", "stocker.db"),
            session_secret=os.environ["STOCKER_SESSION_SECRET"],
            login_password=os.environ["STOCKER_LOGIN_PASSWORD"],
        )
```

- [ ] **Step 4: כתיבת `main.py` מינימלי (בלי DB/routers עדיין)**

```python
# backend/app/main.py
from __future__ import annotations

from fastapi import FastAPI

from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI()
    app.state.settings = settings

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
```

חשוב: **אין** שורת `app = create_app()` ברמת המודול — הרצה תהיה עם
`uvicorn app.main:create_app --factory` (ר' Task 13), כדי שייבוא
המודול בטסטים לא יקרוס על חוסר env vars.

- [ ] **Step 5: כתיבת `conftest.py`**

```python
# backend/tests/conftest.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(
        db_path=str(tmp_path / "test.db"),
        session_secret="test-secret",
        login_password="test-password",
    )


@pytest.fixture
def client(settings):
    app = create_app(settings)
    return TestClient(app)
```

- [ ] **Step 6: כתיבת הטסט הראשון**

```python
# backend/tests/test_health.py
def test_health_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 7: הרצת הטסט ווידוא שעובר**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: PASS (זהו טסט ראשון על קוד שכבר קיים — אין שלב "אדום" נפרד
כאן כי `main.py` נכתב יחד עם הטסט בשלבים 4-6).

- [ ] **Step 8: קומיט**

```bash
git add backend/ .gitignore
git commit -m "feat(backend): scaffold FastAPI app with health endpoint"
```

---

### Task 2: SQLite schema + connection

**Files:**
- Create: `backend/app/db.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Consumes: `Settings.db_path` (Task 1).
- Produces: `get_connection(db_path: str) -> sqlite3.Connection`,
  `init_db(db_path: str) -> None` — בשימוש בכל מודולי הנתונים הבאים
  (portfolio, universe, screener, recommendations, indices).

- [ ] **Step 1: כתיבת הטסט**

```python
# backend/tests/test_db.py
import sqlite3

from app.db import get_connection, init_db

EXPECTED_TABLES = {
    "portfolio_positions",
    "screener_results",
    "universe_tickers",
    "watched_indices",
}


def test_init_db_creates_all_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    conn.close()

    table_names = {row["name"] for row in rows}
    assert EXPECTED_TABLES.issubset(table_names)


def test_get_connection_returns_row_factory(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    conn = get_connection(db_path)
    assert conn.row_factory is sqlite3.Row
    conn.close()
```

- [ ] **Step 2: הרצת הטסט ווידוא שנכשל**

Run: `cd backend && pytest tests/test_db.py -v`
Expected: FAIL עם `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: כתיבת `db.py`**

```python
# backend/app/db.py
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    entry_price REAL NOT NULL,
    stop_loss REAL NOT NULL,
    entry_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    close_date TEXT
);

CREATE TABLE IF NOT EXISTS screener_results (
    run_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    score REAL NOT NULL,
    metrics TEXT NOT NULL,
    PRIMARY KEY (run_date, ticker)
);

CREATE TABLE IF NOT EXISTS universe_tickers (
    ticker TEXT NOT NULL,
    index_name TEXT NOT NULL,
    PRIMARY KEY (ticker, index_name)
);

CREATE TABLE IF NOT EXISTS watched_indices (
    symbol TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: חיווט ל-`main.py`**

```python
# backend/app/main.py
from __future__ import annotations

from fastapi import FastAPI

from app.config import Settings
from app.db import init_db


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI()
    app.state.settings = settings

    init_db(settings.db_path)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
```

- [ ] **Step 5: הרצת הטסטים ווידוא שעוברים**

Run: `cd backend && pytest tests/ -v`
Expected: PASS (כולל `test_health.py` שעדיין אמור לעבוד)

- [ ] **Step 6: קומיט**

```bash
git add backend/app/db.py backend/app/main.py backend/tests/test_db.py
git commit -m "feat(backend): add SQLite schema and connection helpers"
```

---

### Task 3: Indicators (פונקציות טהורות)

**Files:**
- Create: `backend/app/indicators.py`
- Test: `backend/tests/test_indicators.py`

**Interfaces:**
- Produces: `sma(closes: list[float], window: int) -> float | None`,
  `pct_from_52w_high(closes: list[float]) -> float | None`,
  `relative_strength(stock_closes: list[float], benchmark_closes: list[float]) -> float | None`,
  `avg_dollar_volume(closes: list[float], volumes: list[float]) -> float`
  — בשימוש ב-`screener.py` (Task 6).

- [ ] **Step 1: כתיבת הטסטים**

```python
# backend/tests/test_indicators.py
from app.indicators import avg_dollar_volume, pct_from_52w_high, relative_strength, sma


def test_sma_basic():
    assert sma([1, 2, 3, 4, 5], 3) == 4.0


def test_sma_not_enough_data_returns_none():
    assert sma([1, 2], 5) is None


def test_pct_from_52w_high_at_high():
    assert pct_from_52w_high([10, 20, 30]) == 0.0


def test_pct_from_52w_high_below_high():
    result = pct_from_52w_high([10, 20, 30, 27])
    assert round(result, 2) == -10.0


def test_relative_strength_outperforms():
    stock = [100, 110]  # +10%
    benchmark = [100, 105]  # +5%
    result = relative_strength(stock, benchmark)
    assert round(result, 2) == 5.0


def test_relative_strength_insufficient_data_returns_none():
    assert relative_strength([100], [100, 105]) is None


def test_avg_dollar_volume():
    closes = [10, 20]
    volumes = [100, 200]
    # (20*200 + 10*100) / 2 = (4000 + 1000) / 2 = 2500
    assert avg_dollar_volume(closes, volumes) == 2500.0
```

- [ ] **Step 2: הרצת הטסטים ווידוא שנכשלים**

Run: `cd backend && pytest tests/test_indicators.py -v`
Expected: FAIL עם `ModuleNotFoundError: No module named 'app.indicators'`

- [ ] **Step 3: כתיבת `indicators.py`**

```python
# backend/app/indicators.py
from __future__ import annotations


def sma(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def pct_from_52w_high(closes: list[float]) -> float | None:
    if not closes:
        return None
    high = max(closes)
    if high == 0:
        return None
    current = closes[-1]
    return (current - high) / high * 100


def relative_strength(
    stock_closes: list[float], benchmark_closes: list[float]
) -> float | None:
    if len(stock_closes) < 2 or len(benchmark_closes) < 2:
        return None
    if stock_closes[0] == 0 or benchmark_closes[0] == 0:
        return None
    stock_return = (stock_closes[-1] - stock_closes[0]) / stock_closes[0]
    benchmark_return = (benchmark_closes[-1] - benchmark_closes[0]) / benchmark_closes[0]
    return (stock_return - benchmark_return) * 100


def avg_dollar_volume(closes: list[float], volumes: list[float]) -> float:
    if not closes or not volumes:
        return 0.0
    n = min(len(closes), len(volumes))
    total = sum(closes[-i - 1] * volumes[-i - 1] for i in range(n))
    return total / n
```

- [ ] **Step 4: הרצת הטסטים ווידוא שעוברים**

Run: `cd backend && pytest tests/test_indicators.py -v`
Expected: PASS

- [ ] **Step 5: קומיט**

```bash
git add backend/app/indicators.py backend/tests/test_indicators.py
git commit -m "feat(backend): add pure indicator calculation functions"
```

---

### Task 4: Data fetcher (yfinance wrapper)

**Files:**
- Create: `backend/app/data_fetcher.py`
- Test: `backend/tests/test_data_fetcher.py`

**Interfaces:**
- Produces: `PriceHistory` dataclass (`ticker: str, closes: list[float],
  volumes: list[float]`), `fetch_history(ticker: str, period: str = "1y",
  retries: int = 3, backoff_seconds: float = 1.0) -> PriceHistory | None`,
  `fetch_current_price_and_change(ticker: str) -> tuple[float | None, float | None]`
  — בשימוש ב-`screener.py`, `routers/portfolio.py`,
  `routers/recommendations.py`, `routers/indices.py`.

- [ ] **Step 1: כתיבת הטסטים**

```python
# backend/tests/test_data_fetcher.py
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


def test_fetch_current_price_and_change_no_data(monkeypatch):
    monkeypatch.setattr(data_fetcher.yf, "Ticker", lambda t: AlwaysFailsTicker())
    monkeypatch.setattr(data_fetcher.time, "sleep", lambda s: None)
    price, pct_change = data_fetcher.fetch_current_price_and_change("AAPL")
    assert price is None
    assert pct_change is None
```

- [ ] **Step 2: הרצת הטסטים ווידוא שנכשלים**

Run: `cd backend && pytest tests/test_data_fetcher.py -v`
Expected: FAIL עם `ModuleNotFoundError: No module named 'app.data_fetcher'`

- [ ] **Step 3: כתיבת `data_fetcher.py`**

```python
# backend/app/data_fetcher.py
from __future__ import annotations

import time
from dataclasses import dataclass

import yfinance as yf


@dataclass
class PriceHistory:
    ticker: str
    closes: list[float]
    volumes: list[float]


def fetch_history(
    ticker: str, period: str = "1y", retries: int = 3, backoff_seconds: float = 1.0
) -> PriceHistory | None:
    for attempt in range(retries):
        try:
            data = yf.Ticker(ticker).history(period=period)
            if data.empty:
                return None
            return PriceHistory(
                ticker=ticker,
                closes=data["Close"].tolist(),
                volumes=data["Volume"].tolist(),
            )
        except Exception:
            time.sleep(backoff_seconds * (attempt + 1))
    return None


def fetch_current_price_and_change(ticker: str) -> tuple[float | None, float | None]:
    history = fetch_history(ticker, period="5d", retries=2)
    if history is None or not history.closes:
        return None, None
    current = history.closes[-1]
    if len(history.closes) < 2:
        return current, None
    previous = history.closes[-2]
    if previous == 0:
        return current, None
    pct_change = (current - previous) / previous * 100
    return current, pct_change
```

- [ ] **Step 4: הרצת הטסטים ווידוא שעוברים**

Run: `cd backend && pytest tests/test_data_fetcher.py -v`
Expected: PASS

- [ ] **Step 5: קומיט**

```bash
git add backend/app/data_fetcher.py backend/tests/test_data_fetcher.py
git commit -m "feat(backend): add yfinance data fetcher with retry logic"
```

---

### Task 5: Universe (S&P 500 + Nasdaq-100 tickers)

**Files:**
- Create: `backend/app/universe.py`
- Test: `backend/tests/test_universe.py`

**Interfaces:**
- Consumes: `get_connection` (Task 2).
- Produces: `fetch_sp500_tickers() -> list[str]`,
  `fetch_nasdaq100_tickers() -> list[str]`,
  `refresh_universe(db_path: str) -> int`,
  `get_universe_tickers(db_path: str) -> list[str]` — בשימוש ב-`scheduler.py`
  (Task 7).

- [ ] **Step 1: כתיבת הטסטים**

```python
# backend/tests/test_universe.py
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
```

- [ ] **Step 2: הרצת הטסטים ווידוא שנכשלים**

Run: `cd backend && pytest tests/test_universe.py -v`
Expected: FAIL עם `ModuleNotFoundError: No module named 'app.universe'`

- [ ] **Step 3: כתיבת `universe.py`**

```python
# backend/app/universe.py
from __future__ import annotations

import pandas as pd

from app.db import get_connection

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"


def fetch_sp500_tickers() -> list[str]:
    tables = pd.read_html(SP500_URL)
    df = tables[0]
    return [str(t).replace(".", "-") for t in df["Symbol"].tolist()]


def fetch_nasdaq100_tickers() -> list[str]:
    tables = pd.read_html(NASDAQ100_URL)
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
```

- [ ] **Step 4: הרצת הטסטים ווידוא שעוברים**

Run: `cd backend && pytest tests/test_universe.py -v`
Expected: PASS

- [ ] **Step 5: קומיט**

```bash
git add backend/app/universe.py backend/tests/test_universe.py
git commit -m "feat(backend): add S&P 500 + Nasdaq-100 universe refresh"
```

---

### Task 6: Screener

**Files:**
- Create: `backend/app/screener.py`
- Test: `backend/tests/test_screener.py`

**Interfaces:**
- Consumes: `PriceHistory`, `fetch_history` (Task 4); `sma`,
  `pct_from_52w_high`, `relative_strength`, `avg_dollar_volume` (Task 3);
  `get_connection` (Task 2).
- Produces: `ScreenerConfig` dataclass, `ScreenerResult` dataclass
  (`ticker: str, score: float, metrics: dict`),
  `evaluate_ticker(history, benchmark_history, config) -> ScreenerResult | None`,
  `run_screener(tickers: list[str], benchmark_ticker: str = "^GSPC",
  config: ScreenerConfig | None = None, top_n: int = 20) -> list[ScreenerResult]`,
  `save_screener_results(db_path: str, results: list[ScreenerResult],
  run_date: date) -> None` — בשימוש ב-`scheduler.py` (Task 7) ו-
  `routers/recommendations.py` (Task 10).

- [ ] **Step 1: כתיבת הטסטים**

```python
# backend/tests/test_screener.py
import json

from app.data_fetcher import PriceHistory
from app.db import get_connection, init_db
from app.screener import (
    ScreenerConfig,
    evaluate_ticker,
    run_screener,
    save_screener_results,
)
from datetime import date


def _uptrend_closes(n=260, start=50.0, daily_gain=0.15):
    closes = []
    price = start
    for _ in range(n):
        closes.append(price)
        price += daily_gain
    return closes


def test_evaluate_ticker_passes_for_strong_uptrend():
    closes = _uptrend_closes()
    volumes = [1_000_000] * len(closes)
    history = PriceHistory(ticker="AAPL", closes=closes, volumes=volumes)
    benchmark = PriceHistory(
        ticker="^GSPC", closes=_uptrend_closes(daily_gain=0.02), volumes=[0] * 260
    )

    result = evaluate_ticker(history, benchmark, ScreenerConfig())

    assert result is not None
    assert result.ticker == "AAPL"
    assert "relative_strength" in result.metrics


def test_evaluate_ticker_rejects_downtrend():
    closes = list(reversed(_uptrend_closes()))  # יורד עם הזמן
    volumes = [1_000_000] * len(closes)
    history = PriceHistory(ticker="XYZ", closes=closes, volumes=volumes)
    benchmark = PriceHistory(
        ticker="^GSPC", closes=_uptrend_closes(daily_gain=0.02), volumes=[0] * 260
    )

    result = evaluate_ticker(history, benchmark, ScreenerConfig())

    assert result is None


def test_evaluate_ticker_rejects_low_liquidity():
    closes = _uptrend_closes()
    volumes = [10] * len(closes)  # מחזור זעיר
    history = PriceHistory(ticker="ILLIQUID", closes=closes, volumes=volumes)
    benchmark = PriceHistory(
        ticker="^GSPC", closes=_uptrend_closes(daily_gain=0.02), volumes=[0] * 260
    )

    result = evaluate_ticker(history, benchmark, ScreenerConfig())

    assert result is None


def test_run_screener_ranks_and_limits_results(monkeypatch):
    import app.screener as screener_module

    strong = PriceHistory("STRONG", _uptrend_closes(daily_gain=0.30), [1_000_000] * 260)
    weak = PriceHistory("WEAK", _uptrend_closes(daily_gain=0.05), [1_000_000] * 260)
    benchmark = PriceHistory("^GSPC", _uptrend_closes(daily_gain=0.02), [0] * 260)

    histories = {"STRONG": strong, "WEAK": weak, "^GSPC": benchmark}
    monkeypatch.setattr(
        screener_module, "fetch_history", lambda ticker, period="1y": histories.get(ticker)
    )

    results = run_screener(["STRONG", "WEAK"], top_n=1)

    assert len(results) == 1
    assert results[0].ticker == "STRONG"


def test_save_screener_results_persists_and_replaces(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    from app.screener import ScreenerResult

    results = [ScreenerResult(ticker="AAPL", score=12.5, metrics={"pct_from_52w_high": -1.0})]
    save_screener_results(db_path, results, date(2026, 9, 29))

    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM screener_results").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAPL"
    assert json.loads(rows[0]["metrics"])["pct_from_52w_high"] == -1.0
```

- [ ] **Step 2: הרצת הטסטים ווידוא שנכשלים**

Run: `cd backend && pytest tests/test_screener.py -v`
Expected: FAIL עם `ModuleNotFoundError: No module named 'app.screener'`

- [ ] **Step 3: כתיבת `screener.py`**

```python
# backend/app/screener.py
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from app.data_fetcher import PriceHistory, fetch_history
from app.db import get_connection
from app.indicators import avg_dollar_volume, pct_from_52w_high, relative_strength, sma


@dataclass(frozen=True)
class ScreenerConfig:
    sma_short_window: int = 50
    sma_long_window: int = 200
    max_pct_below_52w_high: float = 15.0
    min_avg_dollar_volume: float = 5_000_000.0
    relative_strength_weeks: int = 12


@dataclass
class ScreenerResult:
    ticker: str
    score: float
    metrics: dict


def evaluate_ticker(
    history: PriceHistory,
    benchmark_history: PriceHistory,
    config: ScreenerConfig,
) -> ScreenerResult | None:
    closes = history.closes
    if len(closes) < config.sma_long_window:
        return None

    sma_short = sma(closes, config.sma_short_window)
    sma_long = sma(closes, config.sma_long_window)
    if sma_short is None or sma_long is None:
        return None
    if not (closes[-1] > sma_short > sma_long):
        return None

    pct_high = pct_from_52w_high(closes)
    if pct_high is None or pct_high < -config.max_pct_below_52w_high:
        return None

    dollar_volume = avg_dollar_volume(closes, history.volumes)
    if dollar_volume < config.min_avg_dollar_volume:
        return None

    weeks_of_days = config.relative_strength_weeks * 5
    rel_strength = relative_strength(
        closes[-weeks_of_days:], benchmark_history.closes[-weeks_of_days:]
    )
    if rel_strength is None or rel_strength <= 0:
        return None

    score = rel_strength + (100 + pct_high)
    return ScreenerResult(
        ticker=history.ticker,
        score=score,
        metrics={
            "pct_from_52w_high": pct_high,
            "relative_strength": rel_strength,
            "avg_dollar_volume": dollar_volume,
        },
    )


def run_screener(
    tickers: list[str],
    benchmark_ticker: str = "^GSPC",
    config: ScreenerConfig | None = None,
    top_n: int = 20,
) -> list[ScreenerResult]:
    config = config or ScreenerConfig()
    benchmark_history = fetch_history(benchmark_ticker, period="1y")
    if benchmark_history is None:
        return []

    results: list[ScreenerResult] = []
    for ticker in tickers:
        history = fetch_history(ticker, period="1y")
        if history is None:
            continue
        result = evaluate_ticker(history, benchmark_history, config)
        if result is not None:
            results.append(result)

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]


def save_screener_results(db_path: str, results: list[ScreenerResult], run_date: date) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM screener_results WHERE run_date = ?", (run_date.isoformat(),))
        conn.executemany(
            "INSERT INTO screener_results (run_date, ticker, score, metrics) VALUES (?, ?, ?, ?)",
            [
                (run_date.isoformat(), r.ticker, r.score, json.dumps(r.metrics))
                for r in results
            ],
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: הרצת הטסטים ווידוא שעוברים**

Run: `cd backend && pytest tests/test_screener.py -v`
Expected: PASS

- [ ] **Step 5: קומיט**

```bash
git add backend/app/screener.py backend/tests/test_screener.py
git commit -m "feat(backend): add technical screener with configurable rules"
```

---

### Task 7: Scheduler (ריצת EOD יומית)

**Files:**
- Create: `backend/app/scheduler.py`
- Test: `backend/tests/test_scheduler.py`

**Interfaces:**
- Consumes: `refresh_universe`, `get_universe_tickers` (Task 5);
  `run_screener`, `save_screener_results` (Task 6); `Settings` (Task 1).
- Produces: `run_daily_job(settings: Settings) -> None`,
  `start_scheduler(settings: Settings) -> BackgroundScheduler` — בשימוש
  ב-`main.py` (Task 12).

- [ ] **Step 1: כתיבת הטסט**

```python
# backend/tests/test_scheduler.py
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
```

- [ ] **Step 2: הרצת הטסט ווידוא שנכשל**

Run: `cd backend && pytest tests/test_scheduler.py -v`
Expected: FAIL עם `ModuleNotFoundError: No module named 'app.scheduler'`

- [ ] **Step 3: כתיבת `scheduler.py`**

```python
# backend/app/scheduler.py
from __future__ import annotations

from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.screener import run_screener, save_screener_results
from app.universe import get_universe_tickers, refresh_universe

_scheduler: BackgroundScheduler | None = None


def run_daily_job(settings: Settings) -> None:
    try:
        refresh_universe(settings.db_path)
    except Exception:
        # כשלון רענון היוניברס משאיר את הרשימה השמורה האחרונה —
        # לא זורקים מתוך job מתוזמן.
        pass

    tickers = get_universe_tickers(settings.db_path)
    if not tickers:
        return

    results = run_screener(tickers)
    save_screener_results(settings.db_path, results, date.today())


def start_scheduler(settings: Settings) -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="America/New_York")
    _scheduler.add_job(
        run_daily_job,
        CronTrigger(hour=16, minute=30, day_of_week="mon-fri"),
        args=[settings],
        id="daily_screener",
    )
    _scheduler.start()
    return _scheduler
```

- [ ] **Step 4: הרצת הטסט ווידוא שעובר**

Run: `cd backend && pytest tests/test_scheduler.py -v`
Expected: PASS

- [ ] **Step 5: קומיט**

```bash
git add backend/app/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat(backend): add daily EOD screener scheduler job"
```

---

### Task 8: Auth (סיסמה + session)

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `Settings.login_password`, `Settings.session_secret` (Task 1).
- Produces: `verify_password(submitted: str, expected: str) -> bool`,
  `require_session(request: Request) -> None` (dependency) — בשימוש
  ב-`main.py` להגנה על שאר ה-routers (Tasks 9-11).

- [ ] **Step 1: כתיבת הטסט**

```python
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
```

הערה: `GET /api/portfolio` עדיין לא קיים בשלב הזה — הטסט הזה יעבור
במלואו רק אחרי Task 9. לצורך ה-TDD של המשימה הנוכחית, מוסיפים ל-`main.py`
route זמני `@app.get("/api/portfolio")` שמחזיר `{}` תחת ה-dependency,
ו-Task 9 יחליף אותו ב-router האמיתי.

- [ ] **Step 2: הרצת הטסט ווידוא שנכשל**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: FAIL — `POST /api/auth/login` מחזיר 404 (עדיין לא קיים)

- [ ] **Step 3: כתיבת `auth.py`**

```python
# backend/app/auth.py
from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, status


def verify_password(submitted: str, expected: str) -> bool:
    return hmac.compare_digest(submitted, expected)


def require_session(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
```

- [ ] **Step 4: כתיבת `routers/auth.py`**

```python
# backend/app/routers/__init__.py
```
(קובץ ריק)

```python
# backend/app/routers/auth.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.auth import verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def login(body: LoginRequest, request: Request):
    settings = request.app.state.settings
    if not verify_password(body.password, settings.login_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    request.session["authenticated"] = True
    return {"ok": True}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}
```

- [ ] **Step 5: חיווט ל-`main.py`**

```python
# backend/app/main.py
from __future__ import annotations

from fastapi import Depends, FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.auth import require_session
from app.config import Settings
from app.db import init_db
from app.routers import auth as auth_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI()
    app.state.settings = settings
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)

    init_db(settings.db_path)

    app.include_router(auth_router.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/portfolio", dependencies=[Depends(require_session)])
    def _placeholder_portfolio():
        # Task 9 מחליף את זה ב-router אמיתי
        return {}

    return app
```

- [ ] **Step 6: הרצת הטסטים ווידוא שעוברים**

Run: `cd backend && pytest tests/ -v`
Expected: PASS

- [ ] **Step 7: קומיט**

```bash
git add backend/app/auth.py backend/app/routers backend/app/main.py backend/tests/test_auth.py
git commit -m "feat(backend): add password auth with session cookies"
```

---

### Task 9: Portfolio API

**Files:**
- Create: `backend/app/portfolio.py`
- Create: `backend/app/routers/portfolio.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_portfolio_api.py`

**Interfaces:**
- Consumes: `get_connection` (Task 2); `fetch_current_price_and_change`
  (Task 4); `require_session` (Task 8).
- Produces: `Position` dataclass, `list_open_positions(db_path) ->
  list[Position]`, `open_position(db_path, ticker, entry_price,
  stop_loss) -> int`, `close_position(db_path, position_id) -> bool`;
  router עם `GET /api/portfolio`, `POST /api/portfolio`,
  `POST /api/portfolio/{id}/sell`.

- [ ] **Step 1: כתיבת הטסט**

```python
# backend/tests/test_portfolio_api.py
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
```

`pnl_pct` הוא שדה חדש בתשובת ה-API (% רווח/הפסד מהכניסה) — נשים לב
שהוא נקרא `pnl_pct` ולא `pct_change` (ששמור לשינוי היומי, ר' Task 10-11)
כדי שלא יהיה בלבול בין שני מספרים שונים.

- [ ] **Step 2: הרצת הטסט ווידוא שנכשל**

Run: `cd backend && pytest tests/test_portfolio_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.portfolio'`
(או 404/500 על `/api/portfolio` בפועל)

- [ ] **Step 3: כתיבת `portfolio.py`**

```python
# backend/app/portfolio.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.db import get_connection


@dataclass
class Position:
    id: int
    ticker: str
    entry_price: float
    stop_loss: float
    entry_date: str
    status: str
    close_date: str | None


def list_open_positions(db_path: str) -> list[Position]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM portfolio_positions WHERE status = 'open' ORDER BY entry_date DESC"
        ).fetchall()
        return [Position(**dict(row)) for row in rows]
    finally:
        conn.close()


def open_position(db_path: str, ticker: str, entry_price: float, stop_loss: float) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO portfolio_positions (ticker, entry_price, stop_loss, entry_date, status) "
            "VALUES (?, ?, ?, ?, 'open')",
            (ticker.upper(), entry_price, stop_loss, date.today().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def close_position(db_path: str, position_id: int) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "UPDATE portfolio_positions SET status = 'closed', close_date = ? "
            "WHERE id = ? AND status = 'open'",
            (date.today().isoformat(), position_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
```

- [ ] **Step 4: כתיבת `routers/portfolio.py`**

```python
# backend/app/routers/portfolio.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import portfolio
from app.data_fetcher import fetch_current_price_and_change

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class BuyRequest(BaseModel):
    ticker: str
    entry_price: float
    stop_loss: float


@router.get("")
def list_positions(request: Request):
    db_path = request.app.state.settings.db_path
    positions = portfolio.list_open_positions(db_path)

    result = []
    for p in positions:
        current_price, pct_change = fetch_current_price_and_change(p.ticker)
        pnl_pct = None
        if current_price is not None and p.entry_price:
            pnl_pct = (current_price - p.entry_price) / p.entry_price * 100
        result.append(
            {
                "id": p.id,
                "ticker": p.ticker,
                "entry_price": p.entry_price,
                "stop_loss": p.stop_loss,
                "entry_date": p.entry_date,
                "current_price": current_price,
                "pct_change": pct_change,
                "pnl_pct": pnl_pct,
            }
        )
    return result


@router.post("")
def buy(body: BuyRequest, request: Request):
    db_path = request.app.state.settings.db_path
    position_id = portfolio.open_position(db_path, body.ticker, body.entry_price, body.stop_loss)
    return {"id": position_id}


@router.post("/{position_id}/sell")
def sell(position_id: int, request: Request):
    db_path = request.app.state.settings.db_path
    closed = portfolio.close_position(db_path, position_id)
    if not closed:
        raise HTTPException(status_code=404, detail="Position not found or already closed")
    return {"ok": True}
```

- [ ] **Step 5: חיווט ל-`main.py` (מחליף את ה-placeholder מ-Task 8)**

```python
# backend/app/main.py
from __future__ import annotations

from fastapi import Depends, FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.auth import require_session
from app.config import Settings
from app.db import init_db
from app.routers import auth as auth_router
from app.routers import portfolio as portfolio_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI()
    app.state.settings = settings
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)

    init_db(settings.db_path)

    app.include_router(auth_router.router)
    app.include_router(portfolio_router.router, dependencies=[Depends(require_session)])

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
```

- [ ] **Step 6: הרצת הטסטים ווידוא שעוברים**

Run: `cd backend && pytest tests/ -v`
Expected: PASS

- [ ] **Step 7: קומיט**

```bash
git add backend/app/portfolio.py backend/app/routers/portfolio.py backend/app/main.py backend/tests/test_portfolio_api.py
git commit -m "feat(backend): add virtual portfolio CRUD API"
```

---

### Task 10: Recommendations API

**Files:**
- Create: `backend/app/routers/recommendations.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_recommendations_api.py`

**Interfaces:**
- Consumes: `get_connection` (Task 2); `fetch_current_price_and_change`
  (Task 4); `require_session` (Task 8); טבלת `screener_results` (Task 6).
- Produces: router עם `GET /api/recommendations` המחזיר
  `{"run_date": str | None, "results": [...]}`.

- [ ] **Step 1: כתיבת הטסט**

```python
# backend/tests/test_recommendations_api.py
from datetime import date

import app.routers.recommendations as recommendations_router
from app.db import get_connection
from app.screener import ScreenerResult, save_screener_results


def _login(client):
    client.post("/api/auth/login", json={"password": "test-password"})


def test_recommendations_empty_when_no_runs_yet(client):
    _login(client)
    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    assert resp.json() == {"run_date": None, "results": []}


def test_recommendations_returns_latest_run_sorted_by_score(client, settings, monkeypatch):
    results = [
        ScreenerResult(ticker="AAPL", score=10.0, metrics={"pct_from_52w_high": -1.0}),
        ScreenerResult(ticker="MSFT", score=20.0, metrics={"pct_from_52w_high": -0.5}),
    ]
    save_screener_results(settings.db_path, results, date.today())

    monkeypatch.setattr(
        recommendations_router, "fetch_current_price_and_change", lambda t: (150.0, 1.2)
    )
    _login(client)

    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_date"] == date.today().isoformat()
    tickers_in_order = [r["ticker"] for r in body["results"]]
    assert tickers_in_order == ["MSFT", "AAPL"]
    assert body["results"][0]["current_price"] == 150.0
    assert body["results"][0]["pct_change"] == 1.2
    assert body["results"][0]["pct_from_52w_high"] == -0.5
```

- [ ] **Step 2: הרצת הטסט ווידוא שנכשל**

Run: `cd backend && pytest tests/test_recommendations_api.py -v`
Expected: FAIL — `404 Not Found` על `GET /api/recommendations`

- [ ] **Step 3: כתיבת `routers/recommendations.py`**

```python
# backend/app/routers/recommendations.py
from __future__ import annotations

import json

from fastapi import APIRouter, Request

from app.data_fetcher import fetch_current_price_and_change
from app.db import get_connection

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
def get_recommendations(request: Request):
    db_path = request.app.state.settings.db_path
    conn = get_connection(db_path)
    try:
        latest = conn.execute(
            "SELECT MAX(run_date) AS run_date FROM screener_results"
        ).fetchone()
        run_date = latest["run_date"] if latest else None
        if run_date is None:
            return {"run_date": None, "results": []}

        rows = conn.execute(
            "SELECT ticker, score, metrics FROM screener_results "
            "WHERE run_date = ? ORDER BY score DESC",
            (run_date,),
        ).fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        current_price, pct_change = fetch_current_price_and_change(row["ticker"])
        results.append(
            {
                "ticker": row["ticker"],
                "score": row["score"],
                "current_price": current_price,
                "pct_change": pct_change,
                **json.loads(row["metrics"]),
            }
        )
    return {"run_date": run_date, "results": results}
```

- [ ] **Step 4: חיווט ל-`main.py`**

הוסף ל-imports: `from app.routers import recommendations as recommendations_router`
והוסף שורה אחרי רישום `portfolio_router`:

```python
    app.include_router(
        recommendations_router.router, dependencies=[Depends(require_session)]
    )
```

- [ ] **Step 5: הרצת הטסטים ווידוא שעוברים**

Run: `cd backend && pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: קומיט**

```bash
git add backend/app/routers/recommendations.py backend/app/main.py backend/tests/test_recommendations_api.py
git commit -m "feat(backend): add recommendations API from latest screener run"
```

---

### Task 11: Indices API

**Files:**
- Create: `backend/app/routers/indices.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_indices_api.py`

**Interfaces:**
- Consumes: `get_connection` (Task 2); `fetch_current_price_and_change`
  (Task 4); `require_session` (Task 8).
- Produces: router עם `GET /api/indices`, `POST /api/indices`,
  `DELETE /api/indices/{symbol}`.

- [ ] **Step 1: כתיבת הטסט**

```python
# backend/tests/test_indices_api.py
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
```

- [ ] **Step 2: הרצת הטסט ווידוא שנכשל**

Run: `cd backend && pytest tests/test_indices_api.py -v`
Expected: FAIL — `404 Not Found` על `GET /api/indices`

- [ ] **Step 3: כתיבת `routers/indices.py`**

```python
# backend/app/routers/indices.py
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.data_fetcher import fetch_current_price_and_change
from app.db import get_connection

router = APIRouter(prefix="/api/indices", tags=["indices"])


class AddIndexRequest(BaseModel):
    symbol: str
    display_name: str


@router.get("")
def list_indices(request: Request):
    db_path = request.app.state.settings.db_path
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT symbol, display_name FROM watched_indices ORDER BY sort_order"
        ).fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        current_price, pct_change = fetch_current_price_and_change(row["symbol"])
        result.append(
            {
                "symbol": row["symbol"],
                "display_name": row["display_name"],
                "current_price": current_price,
                "pct_change": pct_change,
            }
        )
    return result


@router.post("")
def add_index(body: AddIndexRequest, request: Request):
    db_path = request.app.state.settings.db_path
    conn = get_connection(db_path)
    try:
        max_order_row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) AS m FROM watched_indices"
        ).fetchone()
        next_order = max_order_row["m"] + 1
        conn.execute(
            "INSERT OR REPLACE INTO watched_indices (symbol, display_name, sort_order) "
            "VALUES (?, ?, ?)",
            (body.symbol.upper(), body.display_name, next_order),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@router.delete("/{symbol}")
def remove_index(symbol: str, request: Request):
    db_path = request.app.state.settings.db_path
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM watched_indices WHERE symbol = ?", (symbol.upper(),))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
```

- [ ] **Step 4: חיווט ל-`main.py`**

הוסף ל-imports: `from app.routers import indices as indices_router`
והוסף שורה נוספת:

```python
    app.include_router(indices_router.router, dependencies=[Depends(require_session)])
```

- [ ] **Step 5: הרצת הטסטים ווידוא שעוברים**

Run: `cd backend && pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: קומיט**

```bash
git add backend/app/routers/indices.py backend/app/main.py backend/tests/test_indices_api.py
git commit -m "feat(backend): add user-managed indices watchlist API"
```

---

### Task 12: אינטגרציה מלאה + הגשת קבצי frontend סטטיים

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`
- Test: `backend/tests/test_integration_flow.py`

**Interfaces:**
- Consumes: כל ה-routers (Tasks 8-11); `start_scheduler` (Task 7).
- Produces: `create_app(settings=None, start_scheduler_job: bool = True)`
  — מחבר סוף-סוף את `start_scheduler` (שהוגדר ב-Task 7 אך לא חובר עד
  כה) ל-startup של האפליקציה, עם flag לכיבוי בטסטים; ומגיש גם
  `frontend/dist` תחת `/` כשהתיקייה קיימת (יעודכן בפועל בפלאן
  ה-frontend).

- [ ] **Step 1: כתיבת טסט אינטגרציה**

```python
# backend/tests/test_integration_flow.py
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
        "/api/portfolio", json={"ticker": "AAPL", "entry_price": 100.0, "stop_loss": 90.0}
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


def test_create_app_skips_scheduler_when_disabled(settings, monkeypatch):
    import app.main as main_module

    started = {}
    monkeypatch.setattr(
        main_module, "start_scheduler", lambda s: started.setdefault("called", True)
    )

    main_module.create_app(settings, start_scheduler_job=False)

    assert "called" not in started
```

- [ ] **Step 2: הרצת הטסט ווידוא שהחלק החדש נכשל**

Run: `cd backend && pytest tests/test_integration_flow.py -v`
Expected: הטסטים הקיימים (flow) עוברים; שני הטסטים החדשים
(`test_create_app_starts_scheduler_by_default`,
`test_create_app_skips_scheduler_when_disabled`) נכשלים, כי `main.py`
עדיין לא מייבא/מפעיל את `start_scheduler` בכלל.

- [ ] **Step 3: עדכון `conftest.py` — כיבוי ה-scheduler בטסטים**

```python
# backend/tests/conftest.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(
        db_path=str(tmp_path / "test.db"),
        session_secret="test-secret",
        login_password="test-password",
    )


@pytest.fixture
def client(settings):
    app = create_app(settings, start_scheduler_job=False)
    return TestClient(app)
```

- [ ] **Step 4: הוספת הגשת קבצי frontend סטטיים + חיווט ה-scheduler ל-`main.py`**

```python
# backend/app/main.py
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import require_session
from app.config import Settings
from app.db import init_db
from app.routers import auth as auth_router
from app.routers import indices as indices_router
from app.routers import portfolio as portfolio_router
from app.routers import recommendations as recommendations_router
from app.scheduler import start_scheduler


def create_app(settings: Settings | None = None, start_scheduler_job: bool = True) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI()
    app.state.settings = settings
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)

    init_db(settings.db_path)

    app.include_router(auth_router.router)
    app.include_router(portfolio_router.router, dependencies=[Depends(require_session)])
    app.include_router(
        recommendations_router.router, dependencies=[Depends(require_session)]
    )
    app.include_router(indices_router.router, dependencies=[Depends(require_session)])

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    if start_scheduler_job:
        start_scheduler(settings)

    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app
```

`start_scheduler` (Task 7) שומר singleton גלובלי (`_scheduler`) כדי
שלא יופעלו כמה ריצות cron מקבילות אם `create_app` נקרא יותר מפעם אחת
בתהליך; ב-production זה קורה פעם אחת בלבד (uvicorn `--factory`), כך
שזה לא בעייתי.

- [ ] **Step 5: הרצת כל חבילת הטסטים**

Run: `cd backend && pytest tests/ -v`
Expected: PASS (כל הטסטים מ-Tasks 1-12, כולל שני טסטי ה-scheduler
מ-Step 1)

- [ ] **Step 6: קומיט**

```bash
git add backend/app/main.py backend/tests/conftest.py backend/tests/test_integration_flow.py
git commit -m "test(backend): wire daily scheduler into app startup, serve static frontend"
```

---

### Task 13: Dockerfile + README

**Files:**
- Create: `backend/Dockerfile`
- Create: `README.md`

**Interfaces:**
- Consumes: `create_app` factory (Task 1-12), `requirements.txt` (Task 1).
- Produces: תמונת Docker שרצה עם `uvicorn app.main:create_app --factory`.

- [ ] **Step 1: כתיבת `backend/Dockerfile`**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

ENV STOCKER_DB_PATH=/data/stocker.db
EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: כתיבת `README.md`**

```markdown
# Stocker

אפליקציית web אישית למעקב מניות: סקרינר יומי על S&P500+Nasdaq-100,
תיק השקעות וירטואלי, ומסך מדדים.

## הרצה מקומית (backend בלבד, ללא frontend עדיין)

\`\`\`bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export STOCKER_SESSION_SECRET="change-me"
export STOCKER_LOGIN_PASSWORD="change-me"
export STOCKER_DB_PATH="./stocker.db"

uvicorn app.main:create_app --factory --reload
\`\`\`

בדיקת תקינות: \`curl http://localhost:8000/api/health\`

## בדיקות

\`\`\`bash
cd backend
pytest tests/ -v
\`\`\`

## Docker

\`\`\`bash
docker build -f backend/Dockerfile -t stocker-backend .
docker run --rm -p 8000:8000 \
  -e STOCKER_SESSION_SECRET=change-me \
  -e STOCKER_LOGIN_PASSWORD=change-me \
  stocker-backend
\`\`\`

## מצב הפרויקט

- ✅ Backend API מלא (auth, portfolio, recommendations, indices, screener יומי)
- ⏳ Frontend (React) — פלאן נפרד
- ⏳ פריסה לענן — פלאן נפרד
```

- [ ] **Step 3: בדיקה ידנית של ה-Docker build**

```bash
docker build -f backend/Dockerfile -t stocker-backend .
docker run --rm -p 8000:8000 -e STOCKER_SESSION_SECRET=x -e STOCKER_LOGIN_PASSWORD=y stocker-backend &
sleep 2
curl http://localhost:8000/api/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: קומיט**

```bash
git add backend/Dockerfile README.md
git commit -m "chore(backend): add Dockerfile and README with run instructions"
```
