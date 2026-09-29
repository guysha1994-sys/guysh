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
