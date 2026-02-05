"""Vehicle API routes for AxleLore."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


class VehicleBase(BaseModel):
    """Base vehicle schema."""
    vehicle_type: str = Field(..., description="Vehicle type code (e.g., 'fzj80')")
    nickname: Optional[str] = Field(None, max_length=100)
    year: Optional[int] = Field(None, ge=1950, le=2030)
    vin: Optional[str] = Field(None, max_length=17)
    current_mileage: Optional[int] = Field(None, ge=0)


class VehicleCreate(VehicleBase):
    """Schema for creating vehicle."""
    pass


class VehicleUpdate(BaseModel):
    """Schema for updating vehicle."""
    nickname: Optional[str] = None
    current_mileage: Optional[int] = None
    year: Optional[int] = None


class VehicleRead(VehicleBase):
    """Schema for reading vehicle."""
    id: int
    created_at: datetime
    updated_at: datetime
    display_name: str = ""
    
    class Config:
        from_attributes = True


@router.get("/", response_model=list[VehicleRead])
async def list_vehicles() -> list[VehicleRead]:
    """List all vehicles."""
    # TODO: Implement database query
    return []


@router.post("/", response_model=VehicleRead)
async def create_vehicle(vehicle: VehicleCreate) -> VehicleRead:
    """Create a new vehicle."""
    # TODO: Implement vehicle creation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{vehicle_id}", response_model=VehicleRead)
async def get_vehicle(vehicle_id: int) -> VehicleRead:
    """Get a specific vehicle by ID."""
    # TODO: Implement vehicle retrieval
    raise HTTPException(status_code=404, detail="Vehicle not found")


@router.put("/{vehicle_id}", response_model=VehicleRead)
async def update_vehicle(vehicle_id: int, vehicle: VehicleUpdate) -> VehicleRead:
    """Update a vehicle."""
    # TODO: Implement vehicle update
    raise HTTPException(status_code=404, detail="Vehicle not found")


@router.delete("/{vehicle_id}")
async def delete_vehicle(vehicle_id: int) -> dict:
    """Delete a vehicle and all associated data."""
    # TODO: Implement vehicle deletion
    return {"status": "ok", "message": f"Vehicle {vehicle_id} deleted"}


@router.get("/types/")
async def list_vehicle_types() -> list[dict]:
    """List all supported vehicle types."""
    return [
        {
            "type": "fzj80",
            "name": "Toyota Land Cruiser FZJ80",
            "years": [1993, 1994, 1995, 1996, 1997],
            "engine": "1FZ-FE"
        }
        # More vehicle types will be added
    ]
