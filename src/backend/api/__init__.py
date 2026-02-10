"""API router initialization."""
from fastapi import APIRouter

from backend.api.chat import router as chat_router
from backend.api.kb import router as kb_router
from backend.api.obd2 import router as obd2_router
from backend.api.service import router as service_router
from backend.api.vehicles import router as vehicles_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(chat_router)
api_router.include_router(vehicles_router)
api_router.include_router(service_router)
api_router.include_router(obd2_router)
api_router.include_router(kb_router)
