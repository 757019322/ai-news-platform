from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from routers import ai, favorite, history, news, users
from scraper.runner import run_scraper
from scraper.scheduler import start_scheduler, stop_scheduler
from services.embedding import embed_all_news
from utils.exception_handlers import register_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("App startup — running initial scrape...")
    try:
        await run_scraper()
    except Exception as exc:
        logger.error("Initial scrape failed (non-fatal): %s", exc)

    logger.info("Building embedding index...")
    try:
        await embed_all_news()
    except Exception as exc:
        logger.error("Embedding index build failed (non-fatal): %s", exc)

    try:
        start_scheduler()
    except Exception as exc:
        logger.error("Scheduler failed to start (non-fatal): %s", exc)

    yield

    try:
        stop_scheduler()
    except Exception as exc:
        logger.error("Scheduler failed to stop cleanly: %s", exc)


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI News Platform API",
        description="Backend service for the AI News Platform (FastAPI + MySQL + SQLAlchemy async).",
        version="1.0.0",
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    cors_origins_env = os.getenv("CORS_ORIGINS", "").strip()
    if cors_origins_env and cors_origins_env != "*":
        allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
        allow_credentials = True
    else:
        allow_origins = ["*"]
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok"}

    _admin_secret = os.getenv("ADMIN_SECRET", "")

    async def verify_admin(x_admin_secret: str = Header(..., alias="X-Admin-Secret")):
        if not _admin_secret or x_admin_secret != _admin_secret:
            raise HTTPException(status_code=403, detail="Forbidden.")

    @app.post("/admin/scrape", tags=["admin"], dependencies=[Depends(verify_admin)])
    async def trigger_scrape():
        await run_scraper()
        await embed_all_news()
        return {"status": "ok", "message": "Scrape and embedding complete."}

    app.include_router(news.router)
    app.include_router(users.router)
    app.include_router(favorite.router)
    app.include_router(history.router)
    app.include_router(ai.router)

    return app


app = create_app()
