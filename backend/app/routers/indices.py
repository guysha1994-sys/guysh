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
