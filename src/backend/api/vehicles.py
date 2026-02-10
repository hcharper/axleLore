"""Vehicle API routes — CRUD operations backed by SQLite."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.session import get_session
from backend.services import vehicle_service

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class VehicleCreate(BaseModel):
    vehicle_type: str = Field(..., description="Vehicle type code, e.g. 'fzj80'")
    nickname: Optional[str] = Field(None, max_length=100)
    year: Optional[int] = Field(None, ge=1950, le=2030)
    vin: Optional[str] = Field(None, max_length=17)
    current_mileage: Optional[int] = Field(None, ge=0)


class VehicleUpdate(BaseModel):
    nickname: Optional[str] = None
    current_mileage: Optional[int] = None
    year: Optional[int] = None
    vin: Optional[str] = None


class VehicleOut(BaseModel):
    id: int
    vehicle_type: str
    nickname: Optional[str] = None
    year: Optional[int] = None
    vin: Optional[str] = None
    current_mileage: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[VehicleOut])
async def list_vehicles(session: AsyncSession = Depends(get_session)):
    vehicles = await vehicle_service.list_vehicles(session)
    return vehicles


@router.post("/", response_model=VehicleOut, status_code=201)
async def create_vehicle(
    body: VehicleCreate,
    session: AsyncSession = Depends(get_session),
):
    # Validate that vehicle_type has a config
    try:
        vehicle_service.load_config(body.vehicle_type)
    except FileNotFoundError:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported vehicle type: {body.vehicle_type}",
        )

    vehicle = await vehicle_service.create_vehicle(
        session,
        vehicle_type=body.vehicle_type,
        nickname=body.nickname,
        year=body.year,
        vin=body.vin,
        current_mileage=body.current_mileage,
    )
    return vehicle


@router.get("/types")
async def list_vehicle_types():
    """List all supported vehicle types (from YAML configs)."""
    return vehicle_service.get_supported_vehicles()


@router.get("/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(
    vehicle_id: int,
    session: AsyncSession = Depends(get_session),
):
    vehicle = await vehicle_service.get_vehicle(session, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: int,
    body: VehicleUpdate,
    session: AsyncSession = Depends(get_session),
):
    vehicle = await vehicle_service.update_vehicle(
        session,
        vehicle_id,
        nickname=body.nickname,
        current_mileage=body.current_mileage,
        year=body.year,
        vin=body.vin,
    )
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.delete("/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: int,
    session: AsyncSession = Depends(get_session),
):
    ok = await vehicle_service.delete_vehicle(session, vehicle_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"status": "ok", "message": f"Vehicle {vehicle_id} deleted"}
