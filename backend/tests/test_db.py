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


import sqlite3 as _sqlite3


def test_init_db_adds_quantity_column_to_existing_table(tmp_path):
    db_path = str(tmp_path / "test.db")
    # simulate an old DB without the quantity column
    conn = _sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE portfolio_positions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL, "
        "entry_price REAL NOT NULL, stop_loss REAL NOT NULL, "
        "entry_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', "
        "close_date TEXT)"
    )
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = get_connection(db_path)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(portfolio_positions)")}
    conn.close()
    assert "quantity" in columns
