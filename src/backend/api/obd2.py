"""OBD2 API routes — DTCs, live sensor data, adapter status."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.config import settings
from backend.services import obd2_service

router = APIRouter(prefix="/obd2", tags=["obd2"])


@router.get("/status")
async def obd2_status():
    if not settings.obd2_enabled:
        return {"enabled": False, "message": "OBD2 is disabled in configuration"}
    return {"enabled": True, **obd2_service.status()}


@router.post("/connect")
async def obd2_connect():
    if not settings.obd2_enabled:
        raise HTTPException(status_code=400, detail="OBD2 is disabled in configuration")
    ok = obd2_service.connect()
    if not ok:
        raise HTTPException(status_code=503, detail="Failed to connect to OBD2 adapter")
    return {"status": "connected", **obd2_service.status()}


@router.post("/disconnect")
async def obd2_disconnect():
    obd2_service.disconnect()
    return {"status": "disconnected"}


@router.get("/dtcs")
async def read_dtcs():
    if not obd2_service.is_connected:
        raise HTTPException(status_code=400, detail="OBD2 not connected")
    dtcs = obd2_service.read_dtcs()
    return {"count": len(dtcs), "dtcs": [{"code": d.code, "description": d.description, "status": d.status} for d in dtcs]}


@router.post("/dtcs/clear")
async def clear_dtcs():
    if not obd2_service.is_connected:
        raise HTTPException(status_code=400, detail="OBD2 not connected")
    ok = obd2_service.clear_dtcs()
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to clear DTCs")
    return {"status": "cleared"}


@router.get("/sensors")
async def read_sensors():
    if not obd2_service.is_connected:
        raise HTTPException(status_code=400, detail="OBD2 not connected")
    snap = obd2_service.read_sensors()
    return {
        "timestamp": snap.timestamp.isoformat(),
        "rpm": snap.rpm,
        "speed_mph": snap.speed_mph,
        "coolant_temp_f": snap.coolant_temp_f,
        "intake_temp_f": snap.intake_temp_f,
        "throttle_pct": snap.throttle_pct,
        "engine_load_pct": snap.engine_load_pct,
    }
