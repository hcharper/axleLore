"""OBD2 API routes — DTCs, live sensor data, adapter status, WebSocket live feed."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.core.config import settings
from backend.services import obd2_service

logger = logging.getLogger(__name__)

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


@router.websocket("/live")
async def obd2_live(ws: WebSocket):
    """WebSocket endpoint for live OBD-II sensor data.

    Polls ``obd2_service.read_sensors()`` at ~500 ms intervals and pushes
    JSON frames to the connected client.  Clients can send a JSON message
    with ``{"interval_ms": 1000}`` to change the polling rate (clamped to
    200–5000 ms).

    If OBD2 is not enabled or not connected, the socket sends an error
    frame and closes.
    """
    await ws.accept()

    if not settings.obd2_enabled:
        await ws.send_json({"error": "OBD2 is disabled in configuration"})
        await ws.close(code=1008)
        return

    if not obd2_service.is_connected:
        await ws.send_json({"error": "OBD2 adapter not connected"})
        await ws.close(code=1008)
        return

    interval_s = 0.5  # default 500 ms

    async def _read_control():
        """Listen for client control messages (non-blocking)."""
        nonlocal interval_s
        try:
            while True:
                data = await ws.receive_json()
                if "interval_ms" in data:
                    ms = max(200, min(5000, int(data["interval_ms"])))
                    interval_s = ms / 1000.0
                    logger.debug("OBD2 WS interval changed to %d ms", ms)
        except (WebSocketDisconnect, Exception):
            pass

    control_task = asyncio.create_task(_read_control())

    try:
        while True:
            snap = obd2_service.read_sensors()
            await ws.send_json({
                "timestamp": snap.timestamp.isoformat(),
                "rpm": snap.rpm,
                "speed_mph": snap.speed_mph,
                "coolant_temp_f": snap.coolant_temp_f,
                "intake_temp_f": snap.intake_temp_f,
                "throttle_pct": snap.throttle_pct,
                "engine_load_pct": snap.engine_load_pct,
            })
            await asyncio.sleep(interval_s)
    except WebSocketDisconnect:
        logger.debug("OBD2 WebSocket client disconnected")
    except Exception as exc:
        logger.error("OBD2 WebSocket error: %s", exc)
    finally:
        control_task.cancel()
