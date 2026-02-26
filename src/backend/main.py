"""Main FastAPI application for RigSherpa backend.

Targets: Raspberry Pi 5 (8 GB) · Qwen3 1.7B via Ollama · ChromaDB · SQLite
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.core.config import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

Path(settings.logs_dir).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s  %(name)-25s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Frontend static build directory
_FRONTEND_BUILD = settings.project_root / "src" / "frontend" / "build"


# ---------------------------------------------------------------------------
# Lifespan — real initialisation
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # 1. Database
    from backend.models.session import init_db
    await init_db()
    logger.info("Database initialised")

    # 2. Vector store — ensure collections exist
    from backend.services import rag_service
    rag_service.ensure_collections(settings.default_vehicle)
    logger.info("ChromaDB collections ready")

    # 3. Ollama health check
    from backend.services import chat_service
    ollama_status = await chat_service.check_health()
    if ollama_status["status"] == "ok":
        logger.info("Ollama OK — models: %s", ", ".join(ollama_status["models"]))
    else:
        logger.warning("Ollama not reachable — chat will fail until it starts")

    # 4. OBD2
    if settings.obd2_enabled:
        from backend.services import obd2_service
        if obd2_service.connect():
            logger.info("OBD2 adapter connected")
        else:
            logger.warning("OBD2 adapter not available")

    logger.info("Startup complete")
    yield

    # Shutdown
    logger.info("Shutting down…")
    await chat_service.close()
    if settings.obd2_enabled:
        from backend.services import obd2_service
        obd2_service.disconnect()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local LLM-powered vehicle assistant for Raspberry Pi",
    docs_url="/docs" if settings.debug else "/docs",  # always on for now
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health / info  (registered before API routers)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    from backend.services import chat_service, rag_service, obd2_service

    ollama = await chat_service.check_health()
    kb = rag_service.get_stats(settings.default_vehicle)

    return JSONResponse(
        content={
            "status": "healthy",
            "version": settings.app_version,
            "services": {
                "database": "ok",
                "llm": ollama["status"],
                "llm_models": ollama.get("models", []),
                "vector_store": f"{kb['total_chunks']} chunks",
                "obd2": obd2_service.status() if settings.obd2_enabled else {"enabled": False},
            },
        }
    )


@app.get("/api/info")
async def api_info():
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "model": settings.ollama_model,
        "vehicle": settings.default_vehicle,
        "endpoints": {
            "chat": "/api/v1/chat/message",
            "chat_stream": "/api/v1/chat/message/stream",
            "vehicles": "/api/v1/vehicles",
            "service": "/api/v1/service",
            "obd2": "/api/v1/obd2",
            "obd2_live": "/api/v1/obd2/live",
            "kb": "/api/v1/kb/status",
            "system_device": "/api/v1/system/device",
            "system_version": "/api/v1/system/version",
            "health": "/health",
            "docs": "/docs",
        },
    }


# ---------------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------------

from backend.api import api_router  # noqa: E402
app.include_router(api_router)


# ---------------------------------------------------------------------------
# Static frontend serving (SPA fallback)
#
# MUST be mounted AFTER API routers so /api/* routes take precedence.
# ---------------------------------------------------------------------------

if _FRONTEND_BUILD.is_dir():
    app.mount("/_app", StaticFiles(directory=str(_FRONTEND_BUILD / "_app")), name="svelte-immutable")
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_BUILD)), name="static-assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """Serve the SPA index.html for all non-API, non-static paths."""
        # Try to serve an actual file first
        file_path = _FRONTEND_BUILD / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # Fall back to index.html for client-side routing
        return FileResponse(str(_FRONTEND_BUILD / "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "frontend": "not built — run 'npm run build' in src/frontend/",
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
