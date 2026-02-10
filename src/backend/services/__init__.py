"""Services module — singleton service instances for dependency injection."""

from backend.services.chat import ChatService
from backend.services.obd2 import OBD2Service
from backend.services.rag import RAGService
from backend.services.vehicle import VehicleService

# Singleton instances (initialised once at import, lazily connect)
chat_service = ChatService()
rag_service = RAGService()
vehicle_service = VehicleService()
obd2_service = OBD2Service()

__all__ = [
    "ChatService",
    "RAGService",
    "VehicleService",
    "OBD2Service",
    "chat_service",
    "rag_service",
    "vehicle_service",
    "obd2_service",
]
