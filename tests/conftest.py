"""Shared test fixtures for AxleLore.

Provides:
- Mock Ollama (httpx_mock)
- In-memory SQLite database
- Ephemeral ChromaDB (temporary directory)
- Mock OBD2 service
- FastAPI test client
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Environment setup (before importing backend modules)
# ---------------------------------------------------------------------------

# Use in-memory SQLite for tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["OBD2_ENABLED"] = "false"
os.environ["DEBUG"] = "true"


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_engine():
    """Create an in-memory async SQLite engine."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    from backend.models.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provide a clean database session for each test."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# ChromaDB fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def chromadb_dir():
    """Temporary directory for ephemeral ChromaDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def rag_service(chromadb_dir):
    """RAG service with ephemeral ChromaDB."""
    from backend.services.rag import RAGService
    svc = RAGService(persist_dir=chromadb_dir)
    return svc


# ---------------------------------------------------------------------------
# Mock Ollama
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ollama_response():
    """Standard mock Ollama response."""
    return {
        "response": "The 1FZ-FE engine oil capacity is 6.8 quarts with filter.",
        "eval_count": 42,
        "model": "qwen3:1.7b",
    }


@pytest.fixture
def mock_chat_service(mock_ollama_response):
    """ChatService with mocked HTTP client."""
    from backend.services.chat import ChatService, LLMResponse

    svc = ChatService()
    svc.generate = AsyncMock(return_value=LLMResponse(
        content=mock_ollama_response["response"],
        tokens_used=mock_ollama_response["eval_count"],
        model=mock_ollama_response["model"],
    ))

    async def mock_stream(*args, **kwargs):
        for word in mock_ollama_response["response"].split():
            yield word + " "

    svc.generate_stream = mock_stream
    svc.check_health = AsyncMock(return_value={"status": "ok", "models": ["qwen3:1.7b"]})
    return svc


# ---------------------------------------------------------------------------
# Mock OBD2
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_obd2_service():
    """OBD2 service that doesn't require real hardware."""
    from backend.services.obd2 import OBD2Service, SensorSnapshot, DTCInfo
    from datetime import datetime

    svc = OBD2Service()
    svc._connection = MagicMock()
    svc._connection.is_connected.return_value = True
    svc.read_sensors = MagicMock(return_value=SensorSnapshot(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        rpm=800,
        speed_mph=0,
        coolant_temp_f=190,
        intake_temp_f=85,
        throttle_pct=15.0,
        engine_load_pct=20.0,
    ))
    svc.read_dtcs = MagicMock(return_value=[
        DTCInfo(code="P0420", description="Catalyst efficiency below threshold"),
    ])
    return svc


# ---------------------------------------------------------------------------
# Vehicle service fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def vehicle_service():
    """Vehicle service with real YAML configs."""
    from backend.services.vehicle import VehicleService
    config_dir = Path(__file__).parent.parent / "config" / "vehicles"
    return VehicleService(config_dir=config_dir)


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture
def app(mock_chat_service, rag_service, mock_obd2_service, vehicle_service):
    """FastAPI app with mocked services."""
    with patch("backend.services.chat_service", mock_chat_service), \
         patch("backend.services.rag_service", rag_service), \
         patch("backend.services.obd2_service", mock_obd2_service), \
         patch("backend.services.vehicle_service", vehicle_service):
        from backend.main import app as fastapi_app
        yield fastapi_app


@pytest.fixture
def client(app):
    """Synchronous test client for endpoint tests.

    Uses context manager to ensure lifespan events (init_db, etc.) run.
    Tables are dropped and recreated for each test to ensure isolation.
    """
    from backend.models.database import Base
    from backend.models.session import engine

    import asyncio

    async def _reset_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    with TestClient(app) as c:
        # Reset tables after lifespan has run, before yielding to the test
        asyncio.get_event_loop().run_until_complete(_reset_tables())
        yield c
