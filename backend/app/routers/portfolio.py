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
