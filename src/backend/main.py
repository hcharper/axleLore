"""Main FastAPI application for AxleLore backend."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Startup: Initialize services
    logger.info("Initializing database...")
    # TODO: Initialize database connection

    logger.info("Initializing vector store...")
    # TODO: Initialize ChromaDB

    logger.info("Checking Ollama connection...")
    # TODO: Check Ollama availability

    if settings.obd2_enabled:
        logger.info("Initializing OBD2 service...")
        # TODO: Initialize OBD2 service

    logger.info("Application startup complete")

    yield

    # Shutdown: Cleanup
    logger.info("Shutting down application...")
    # TODO: Close database connections
    # TODO: Close OBD2 connection
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local LLM-powered vehicle assistant for Raspberry Pi",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


# Health check endpoint
@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "version": settings.app_version,
        "services": {
            "database": "unknown",  # TODO: Check database connection
            "llm": "unknown",  # TODO: Check Ollama
            "vector_store": "unknown",  # TODO: Check ChromaDB
            "obd2": "disabled" if not settings.obd2_enabled else "unknown",
        },
    }
    return JSONResponse(content=health_status)


# API info endpoint
@app.get("/api/info")
async def api_info() -> dict[str, str | dict[str, str]]:
    """Get API information."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "vehicle": settings.default_vehicle,
        "endpoints": {
            "health": "/health",
            "chat": "/api/chat",
            "obd2": "/api/obd2",
            "service": "/api/service",
            "kb": "/api/kb",
        },
    }


# Include API routers
from backend.api import api_router
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
