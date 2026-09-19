"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.api.errors import register_exception_handlers
from app.config import get_settings
from app.db.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    logger.info("Starting %s (db=%s)", settings.app_name, settings.database_url)
    init_db()
    from app.db.session import SessionLocal
    from app.seed import seed_if_empty

    session = SessionLocal()
    try:
        seed_if_empty(session)
        session.commit()
    finally:
        session.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description="AI-native project planner — Gantt, Excel, MCP agent",
        lifespan=lifespan,
    )
    origins = settings.cors_origin_list
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(api_router)

    if settings.serve_frontend and STATIC_DIR.exists():
        assets = STATIC_DIR / "assets"
        if assets.exists():
            application.mount("/assets", StaticFiles(directory=assets), name="assets")

        @application.get("/")
        async def spa_index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

        @application.get("/{full_path:path}")
        async def spa_fallback(full_path: str) -> FileResponse:
            reserved = ("api/", "health", "docs", "openapi.json", "redoc")
            if full_path.startswith(reserved) or full_path in reserved:
                from fastapi import HTTPException

                raise HTTPException(status_code=404)
            candidate = STATIC_DIR / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(STATIC_DIR / "index.html")

    return application


app = create_app()
