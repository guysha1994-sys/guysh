from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    entry_price REAL NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
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


def _ensure_quantity_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(portfolio_positions)")}
    if "quantity" not in columns:
        conn.execute(
            "ALTER TABLE portfolio_positions ADD COLUMN quantity REAL NOT NULL DEFAULT 0"
        )


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        _ensure_quantity_column(conn)
        conn.commit()
    finally:
        conn.close()
