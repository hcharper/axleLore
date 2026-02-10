"""Device and system information endpoints.

Exposes device identity, software/knowledge-pack version, and update
status for the local management UI and the remote update server.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter

from backend.core.config import settings

router = APIRouter(prefix="/system", tags=["system"])
logger = logging.getLogger(__name__)

_STATE_DIR = Path("/var/lib/axlelore")


def _read_file(path: Path, default: str = "") -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return default


@router.get("/device")
async def device_info():
    """Return device identity and registration status."""
    device_id = _read_file(_STATE_DIR / "device_id", "dev-mode")
    provisioned = (_STATE_DIR / ".provisioned").exists()
    wifi_configured = (_STATE_DIR / ".wifi-configured").exists()
    has_token = (_STATE_DIR / ".token").exists()

    # Hardware info
    hardware = "unknown"
    model_path = Path("/proc/device-tree/model")
    if model_path.exists():
        hardware = model_path.read_text().strip("\x00").strip()

    return {
        "device_id": device_id,
        "hostname": _read_file(Path("/etc/hostname"), "axlelore"),
        "hardware": hardware,
        "provisioned": provisioned,
        "wifi_configured": wifi_configured,
        "registered": has_token,
    }


@router.get("/version")
async def version_info():
    """Return software and knowledge-pack versions."""
    # Software version from settings
    software_version = settings.app_version

    # Knowledge-pack version from manifest
    kb_version = "none"
    kb_stats: dict = {}
    manifest_path = settings.data_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            kb_version = manifest.get("version", "unknown")
            kb_stats = manifest.get("stats", {})
        except Exception:
            pass

    return {
        "software_version": software_version,
        "kb_version": kb_version,
        "vehicle_type": settings.default_vehicle,
        "model": settings.ollama_model,
        "fallback_model": settings.ollama_fallback_model,
        "kb_stats": kb_stats,
    }


@router.get("/update-status")
async def update_status():
    """Return last update check result."""
    # Read from journalctl for the most recent update log
    import subprocess

    try:
        result = subprocess.run(
            ["journalctl", "-t", "axlelore-update", "-n", "5", "--no-pager", "-o", "short-iso"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except Exception:
        lines = []

    return {
        "kb_version": _read_manifest_version(),
        "recent_log": lines,
    }


def _read_manifest_version() -> str:
    manifest_path = settings.data_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            with open(manifest_path) as f:
                return json.load(f).get("version", "unknown")
        except Exception:
            pass
    return "none"
