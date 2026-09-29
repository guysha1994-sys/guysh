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
