"""Service records API routes — owner service log + maintenance schedules."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.session import get_session
from backend.services import vehicle_service

router = APIRouter(prefix="/service", tags=["service"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PartUsed(BaseModel):
    part_number: Optional[str] = None
    name: str
    quantity: int = 1
    cost: Optional[float] = None
    brand: Optional[str] = None


class ServiceRecordCreate(BaseModel):
    service_date: datetime
    service_type: str = Field(..., description="e.g. oil_change, timing_belt, other")
    mileage: Optional[int] = None
    description: Optional[str] = None
    cost: Optional[float] = None
    parts_used: list[PartUsed] = []
    performed_by: str = "self"
    location: Optional[str] = None
    next_service_mileage: Optional[int] = None
    next_service_date: Optional[datetime] = None


class ServiceRecordOut(BaseModel):
    id: int
    vehicle_id: int
    service_date: datetime
    service_type: Optional[str] = None
    mileage: Optional[int] = None
    description: Optional[str] = None
    cost: Optional[float] = None
    parts_used: Optional[list | dict] = None
    performed_by: Optional[str] = None
    location: Optional[str] = None
    next_service_mileage: Optional[int] = None
    next_service_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{vehicle_id}/records", response_model=list[ServiceRecordOut])
async def list_service_records(
    vehicle_id: int,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    records = await vehicle_service.get_service_records(session, vehicle_id, limit=limit)
    return records


@router.post("/{vehicle_id}/records", response_model=ServiceRecordOut, status_code=201)
async def create_service_record(
    vehicle_id: int,
    body: ServiceRecordCreate,
    session: AsyncSession = Depends(get_session),
):
    # Verify vehicle exists
    vehicle = await vehicle_service.get_vehicle(session, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    parts_data = [p.model_dump() for p in body.parts_used] if body.parts_used else None

    record = await vehicle_service.add_service_record(
        session,
        vehicle_id=vehicle_id,
        service_date=body.service_date,
        service_type=body.service_type,
        mileage=body.mileage,
        description=body.description,
        cost=body.cost,
        parts_used=parts_data,
        performed_by=body.performed_by,
        location=body.location,
        next_service_mileage=body.next_service_mileage,
        next_service_date=body.next_service_date,
    )
    return record


@router.delete("/{vehicle_id}/records/{record_id}")
async def delete_service_record(
    vehicle_id: int,
    record_id: int,
    session: AsyncSession = Depends(get_session),
):
    from backend.models.database import ServiceRecord

    record = await session.get(ServiceRecord, record_id)
    if record is None or record.vehicle_id != vehicle_id:
        raise HTTPException(status_code=404, detail="Service record not found")
    await session.delete(record)
    await session.commit()
    return {"status": "ok", "message": f"Service record {record_id} deleted"}


@router.get("/schedules/{vehicle_type}")
async def get_maintenance_schedule(vehicle_type: str):
    """Return maintenance schedule derived from YAML config."""
    try:
        schedules = vehicle_service.get_maintenance_schedule(vehicle_type)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Vehicle type {vehicle_type} not found")
    return {"vehicle_type": vehicle_type, "schedules": schedules}
