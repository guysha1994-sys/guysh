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
