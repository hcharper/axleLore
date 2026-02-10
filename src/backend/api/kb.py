"""Knowledge base status API — inspect ChromaDB collections."""

from __future__ import annotations

from fastapi import APIRouter

from backend.core.config import settings
from backend.services import rag_service

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


@router.get("/status")
async def kb_status():
    """Return chunk counts per collection for the default vehicle."""
    stats = rag_service.get_stats(settings.default_vehicle)
    return stats


@router.get("/status/{vehicle_type}")
async def kb_status_vehicle(vehicle_type: str):
    """Return chunk counts per collection for a specific vehicle type."""
    stats = rag_service.get_stats(vehicle_type)
    return stats
