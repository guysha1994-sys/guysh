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
