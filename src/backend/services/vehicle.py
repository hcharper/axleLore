"""Vehicle management service for RigSherpa.

Loads vehicle YAML configs, queries the database for owner-specific data
(service records, mods, mileage), and assembles the RAG vehicle-context
string injected into every LLM prompt.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

import yaml
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.database import Vehicle, ServiceRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VehicleConfig:
    """Parsed vehicle YAML configuration."""

    vehicle_type: str
    name: str
    production_years: list[int]
    engine: dict = field(default_factory=dict)
    transmission: dict = field(default_factory=dict)
    common_issues: list[dict] = field(default_factory=list)
    modifications: dict = field(default_factory=dict)
    knowledge_sources: dict = field(default_factory=dict)
    # Full raw YAML for richer lookups
    raw: dict = field(default_factory=dict, repr=False)


@dataclass
class VehicleContext:
    """Vehicle context ready for prompt injection."""

    vehicle_type: str
    vehicle_name: str
    year: Optional[int] = None
    nickname: Optional[str] = None
    current_mileage: Optional[int] = None
    engine_code: str = "Unknown"
    modifications: list[str] = field(default_factory=list)
    recent_services: list[str] = field(default_factory=list)
    active_dtcs: list[str] = field(default_factory=list)
    next_service: Optional[str] = None

    def to_prompt_string(self) -> str:
        lines = [f"Vehicle: {self.year or ''} {self.vehicle_name}"]
        if self.nickname:
            lines.append(f"Nickname: {self.nickname}")
        if self.current_mileage:
            lines.append(f"Mileage: {self.current_mileage:,} mi")
        lines.append(f"Engine: {self.engine_code}")
        if self.modifications:
            lines.append(f"Mods: {', '.join(self.modifications)}")
        if self.recent_services:
            lines.append("Recent work:")
            for svc in self.recent_services[:5]:
                lines.append(f"  - {svc}")
        if self.active_dtcs:
            lines.append(f"Active DTCs: {', '.join(self.active_dtcs)}")
        if self.next_service:
            lines.append(f"Next service due: {self.next_service}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class VehicleService:
    """Vehicle configuration + database operations."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or settings.vehicles_config_dir
        self._configs: dict[str, VehicleConfig] = {}

    # -- YAML config ------------------------------------------------------

    def load_config(self, vehicle_type: str) -> VehicleConfig:
        """Load and cache a vehicle YAML config."""
        if vehicle_type in self._configs:
            return self._configs[vehicle_type]

        config_path = self.config_dir / f"{vehicle_type}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(
                f"No configuration found for vehicle type: {vehicle_type}"
            )

        with open(config_path) as fh:
            data = yaml.safe_load(fh)

        cfg = VehicleConfig(
            vehicle_type=data["vehicle_type"],
            name=data["name"],
            production_years=data.get("production_years", []),
            engine=data.get("engine", {}),
            transmission=data.get("transmission", {}),
            common_issues=data.get("common_issues", []),
            modifications=data.get("modifications", {}),
            knowledge_sources=data.get("knowledge_sources", {}),
            raw=data,
        )
        self._configs[vehicle_type] = cfg
        return cfg

    def get_supported_vehicles(self) -> list[dict]:
        vehicles: list[dict] = []
        for path in sorted(self.config_dir.glob("*.yaml")):
            try:
                with open(path) as fh:
                    d = yaml.safe_load(fh)
                vehicles.append(
                    {"type": d["vehicle_type"], "name": d["name"], "years": d.get("production_years", [])}
                )
            except Exception as exc:
                logger.warning("Failed to load %s: %s", path, exc)
        return vehicles

    def get_maintenance_schedule(self, vehicle_type: str) -> list[dict]:
        cfg = self.load_config(vehicle_type)
        schedules: list[dict] = []
        engine_maint = cfg.engine.get("maintenance", {})

        _SCHEDULE_MAP = {
            "oil_change": "Engine oil and filter change",
            "timing_belt": "Replace timing belt and water pump",
            "spark_plugs": "Replace spark plugs",
            "valve_adjustment": "Valve lash adjustment (shim under bucket)",
            "air_filter": "Replace engine air filter",
        }

        for key, desc in _SCHEDULE_MAP.items():
            if key in engine_maint:
                entry: dict = {"service_type": key, "description": desc}
                entry["interval_miles"] = engine_maint[key].get("interval_miles")
                if "interval_months" in engine_maint[key]:
                    entry["interval_months"] = engine_maint[key]["interval_months"]
                schedules.append(entry)

        # Transmission / transfer case / diffs from raw YAML
        trans = cfg.raw.get("transmission", {})
        auto = trans.get("automatic", {})
        if auto:
            schedules.append({
                "service_type": "transmission_service",
                "interval_miles": 30_000,
                "description": f"Change {auto.get('code', 'auto')} transmission fluid and filter",
            })

        tc = cfg.raw.get("transfer_case", {})
        if tc:
            schedules.append({
                "service_type": "transfer_case_service",
                "interval_miles": 30_000,
                "description": "Change transfer case fluid",
            })

        return schedules

    # -- Database operations ----------------------------------------------

    async def create_vehicle(self, session: AsyncSession, **kwargs) -> Vehicle:
        vehicle = Vehicle(**kwargs)
        session.add(vehicle)
        await session.commit()
        await session.refresh(vehicle)
        return vehicle

    async def get_vehicle(self, session: AsyncSession, vehicle_id: int) -> Vehicle | None:
        return await session.get(Vehicle, vehicle_id)

    async def list_vehicles(self, session: AsyncSession) -> Sequence[Vehicle]:
        result = await session.execute(select(Vehicle).order_by(Vehicle.id))
        return result.scalars().all()

    async def update_vehicle(
        self, session: AsyncSession, vehicle_id: int, **kwargs
    ) -> Vehicle | None:
        vehicle = await session.get(Vehicle, vehicle_id)
        if vehicle is None:
            return None
        for key, val in kwargs.items():
            if val is not None and hasattr(vehicle, key):
                setattr(vehicle, key, val)
        await session.commit()
        await session.refresh(vehicle)
        return vehicle

    async def delete_vehicle(self, session: AsyncSession, vehicle_id: int) -> bool:
        vehicle = await session.get(Vehicle, vehicle_id)
        if vehicle is None:
            return False
        await session.delete(vehicle)
        await session.commit()
        return True

    # -- Service records --------------------------------------------------

    async def add_service_record(
        self, session: AsyncSession, vehicle_id: int, **kwargs
    ) -> ServiceRecord:
        record = ServiceRecord(vehicle_id=vehicle_id, **kwargs)
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def get_service_records(
        self, session: AsyncSession, vehicle_id: int, limit: int = 50
    ) -> Sequence[ServiceRecord]:
        result = await session.execute(
            select(ServiceRecord)
            .where(ServiceRecord.vehicle_id == vehicle_id)
            .order_by(desc(ServiceRecord.service_date))
            .limit(limit)
        )
        return result.scalars().all()

    # -- Context assembly -------------------------------------------------

    async def build_context(
        self,
        session: AsyncSession,
        vehicle_id: int,
    ) -> VehicleContext:
        """Build full vehicle context from DB + YAML config."""
        vehicle = await self.get_vehicle(session, vehicle_id)
        if vehicle is None:
            raise ValueError(f"Vehicle {vehicle_id} not found")

        cfg = self.load_config(vehicle.vehicle_type)

        # Recent services
        records = await self.get_service_records(session, vehicle_id, limit=10)
        recent_svcs = [
            f"{r.service_date.strftime('%Y-%m-%d')} @ {r.mileage or '?'} mi — {r.service_type}: {r.description or ''}"
            for r in records
        ]

        return VehicleContext(
            vehicle_type=vehicle.vehicle_type,
            vehicle_name=cfg.name,
            year=vehicle.year,
            nickname=vehicle.nickname,
            current_mileage=vehicle.current_mileage,
            engine_code=cfg.engine.get("code", "Unknown"),
            recent_services=recent_svcs,
        )

    def build_context_from_config(
        self,
        vehicle_type: str,
        year: int | None = None,
        mileage: int | None = None,
        nickname: str | None = None,
    ) -> VehicleContext:
        """Lightweight context from YAML only (no DB)."""
        cfg = self.load_config(vehicle_type)
        return VehicleContext(
            vehicle_type=vehicle_type,
            vehicle_name=cfg.name,
            year=year,
            nickname=nickname,
            current_mileage=mileage,
            engine_code=cfg.engine.get("code", "Unknown"),
        )
