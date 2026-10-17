"""FastAPI entry point. Run: uv run uvicorn app.main:app --reload --port 8000  (from backend/)."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import agent, chat, files, system
from app.core.config import get_settings
from app.core.db import init_db
from app.core.errors import AppError
from app.tools import load_tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    init_db()
    log.info("LLM: %s (configured=%s)", s.llm_model, s.llm_configured)
    log.info("Features: rag=%s ml=%s vision=%s", s.enable_rag, s.enable_ml, s.enable_vision)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    load_tools()
    app = FastAPI(title=s.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(ValueError)
    async def value_error(_: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(system.router)
    app.include_router(chat.router)
    app.include_router(agent.router)
    app.include_router(files.router)

    # Optional modules: imported only when enabled, so a broken/unused module can't break startup.
    if s.enable_rag:
        from app.api import rag

        app.include_router(rag.router)
    if s.enable_ml:
        from app.api import ml

        app.include_router(ml.router)
    if s.enable_vision:
        from app.api import vision

        app.include_router(vision.router)
    return app


app = create_app()
