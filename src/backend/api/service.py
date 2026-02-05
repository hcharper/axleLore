"""Service records API routes for AxleLore."""
from typing import Optional
from datetime import datetime
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/service", tags=["service"])


class ServiceType(str, Enum):
    """Standardized service types."""
    OIL_CHANGE = "oil_change"
    TIRE_ROTATION = "tire_rotation"
    AIR_FILTER = "air_filter"
    BRAKE_INSPECTION = "brake_inspection"
    TIMING_BELT = "timing_belt"
    SPARK_PLUGS = "spark_plugs"
    TRANSMISSION_SERVICE = "transmission_service"
    DIFF_SERVICE = "diff_service"
    COOLANT_FLUSH = "coolant_flush"
    BRAKE_PADS = "brake_pads"
    BRAKE_ROTORS = "brake_rotors"
    SUSPENSION = "suspension"
    ENGINE_REPAIR = "engine_repair"
    LIFT_INSTALL = "lift_install"
    LOCKER_INSTALL = "locker_install"
    OTHER = "other"


class PartUsed(BaseModel):
    """Part used in service."""
    part_number: Optional[str] = None
    name: str
    quantity: int = 1
    cost: Optional[float] = None
    brand: Optional[str] = None


class ServiceRecordBase(BaseModel):
    """Base service record schema."""
    service_date: datetime
    service_type: ServiceType
    mileage: Optional[int] = None
    description: Optional[str] = None
    cost: Optional[float] = None
    parts_used: list[PartUsed] = []
    performed_by: str = "self"
    location: Optional[str] = None
    next_service_mileage: Optional[int] = None
    next_service_date: Optional[datetime] = None
    notes: Optional[str] = None


class ServiceRecordCreate(ServiceRecordBase):
    """Create service record."""
    pass


class ServiceRecordRead(ServiceRecordBase):
    """Read service record."""
    id: int
    vehicle_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/{vehicle_id}/records", response_model=list[ServiceRecordRead])
async def list_service_records(
    vehicle_id: int,
    service_type: Optional[ServiceType] = None,
    limit: int = 100
) -> list[ServiceRecordRead]:
    """List service records for a vehicle."""
    # TODO: Implement database query
    return []


@router.post("/{vehicle_id}/records", response_model=ServiceRecordRead)
async def create_service_record(
    vehicle_id: int,
    record: ServiceRecordCreate
) -> ServiceRecordRead:
    """Create a new service record."""
    # TODO: Implement service record creation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{vehicle_id}/records/{record_id}", response_model=ServiceRecordRead)
async def get_service_record(vehicle_id: int, record_id: int) -> ServiceRecordRead:
    """Get a specific service record."""
    # TODO: Implement record retrieval
    raise HTTPException(status_code=404, detail="Service record not found")


@router.delete("/{vehicle_id}/records/{record_id}")
async def delete_service_record(vehicle_id: int, record_id: int) -> dict:
    """Delete a service record."""
    # TODO: Implement record deletion
    return {"status": "ok", "message": f"Service record {record_id} deleted"}


@router.get("/schedules/{vehicle_type}")
async def get_maintenance_schedule(vehicle_type: str) -> dict:
    """Get maintenance schedule for a vehicle type."""
    # TODO: Load from vehicle config
    if vehicle_type == "fzj80":
        return {
            "vehicle_type": "fzj80",
            "schedules": [
                {
                    "service_type": "oil_change",
                    "interval_miles": 5000,
                    "interval_months": 6,
                    "description": "Engine oil and filter change"
                },
                {
                    "service_type": "tire_rotation",
                    "interval_miles": 7500,
                    "description": "Rotate tires front to back"
                },
                {
                    "service_type": "timing_belt",
                    "interval_miles": 90000,
                    "description": "Replace timing belt and water pump"
                },
                {
                    "service_type": "diff_service",
                    "interval_miles": 30000,
                    "description": "Change front and rear differential fluid"
                },
                {
                    "service_type": "transmission_service",
                    "interval_miles": 30000,
                    "description": "Change transmission fluid and filter"
                },
                {
                    "service_type": "coolant_flush",
                    "interval_miles": 30000,
                    "interval_months": 24,
                    "description": "Flush and replace coolant"
                }
            ]
        }
    raise HTTPException(status_code=404, detail=f"Vehicle type {vehicle_type} not found")
