# backend/app/main.py
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response

from app.auth import require_session
from app.config import Settings
from app.db import init_db
from app.routers import auth as auth_router
from app.routers import indices as indices_router
from app.routers import portfolio as portfolio_router
from app.routers import recommendations as recommendations_router
from app.scheduler import start_scheduler


def create_app(settings: Settings | None = None, start_scheduler_job: bool = True) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI()
    app.state.settings = settings
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)

    init_db(settings.db_path)

    app.include_router(auth_router.router)
    app.include_router(portfolio_router.router, dependencies=[Depends(require_session)])
    app.include_router(
        recommendations_router.router, dependencies=[Depends(require_session)]
    )
    app.include_router(indices_router.router, dependencies=[Depends(require_session)])

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    if start_scheduler_job:
        start_scheduler(settings)

    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

        @app.exception_handler(StarletteHTTPException)
        async def spa_fallback(request: Request, exc: StarletteHTTPException) -> Response:
            if exc.status_code == 404 and not request.url.path.startswith("/api"):
                return FileResponse(frontend_dist / "index.html")
            return JSONResponse(
                {"detail": exc.detail},
                status_code=exc.status_code,
                headers=getattr(exc, "headers", None),
            )

    return app
