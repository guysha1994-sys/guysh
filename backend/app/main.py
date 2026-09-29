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
