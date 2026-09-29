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
    quantity: float
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


def open_position(
    db_path: str, ticker: str, entry_price: float, quantity: float, stop_loss: float
) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO portfolio_positions "
            "(ticker, entry_price, quantity, stop_loss, entry_date, status) "
            "VALUES (?, ?, ?, ?, ?, 'open')",
            (ticker.upper(), entry_price, quantity, stop_loss, date.today().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def add_to_position(db_path: str, position_id: int, quantity: float, price: float) -> bool:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT entry_price, quantity FROM portfolio_positions "
            "WHERE id = ? AND status = 'open'",
            (position_id,),
        ).fetchone()
        if row is None:
            return False

        old_quantity = row["quantity"]
        old_entry_price = row["entry_price"]
        new_quantity = old_quantity + quantity
        new_entry_price = (
            old_quantity * old_entry_price + quantity * price
        ) / new_quantity

        conn.execute(
            "UPDATE portfolio_positions SET entry_price = ?, quantity = ? WHERE id = ?",
            (new_entry_price, new_quantity, position_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def update_stop_loss(db_path: str, position_id: int, stop_loss: float) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "UPDATE portfolio_positions SET stop_loss = ? WHERE id = ? AND status = 'open'",
            (stop_loss, position_id),
        )
        conn.commit()
        return cursor.rowcount > 0
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
