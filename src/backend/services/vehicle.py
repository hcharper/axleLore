"""Vehicle management service for AxleLore."""
from typing import Optional
from pathlib import Path
from dataclasses import dataclass
import yaml
import logging

from backend.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VehicleConfig:
    """Parsed vehicle configuration."""
    vehicle_type: str
    name: str
    production_years: list[int]
    engine: dict
    transmission: dict
    common_issues: list[dict]
    modifications: dict
    knowledge_sources: dict


@dataclass
class VehicleRAGContext:
    """Vehicle context for RAG injection."""
    vehicle_type: str
    vehicle_name: str
    year: Optional[int]
    nickname: Optional[str]
    current_mileage: Optional[int]
    engine_code: str
    modifications: list[str]
    recent_services: list[str]
    next_service: Optional[dict]
    
    def to_prompt_string(self) -> str:
        """Format context for system prompt injection."""
        parts = [
            f"Vehicle: {self.year or ''} {self.vehicle_name}",
        ]
        
        if self.nickname:
            parts.append(f"Nickname: {self.nickname}")
            
        if self.current_mileage:
            parts.append(f"Current Mileage: {self.current_mileage:,} miles")
            
        parts.append(f"Engine: {self.engine_code}")
        
        if self.modifications:
            parts.append(f"Modifications: {', '.join(self.modifications)}")
            
        if self.recent_services:
            parts.append("Recent Services:")
            for service in self.recent_services[:5]:
                parts.append(f"  - {service}")
                
        if self.next_service:
            parts.append(f"Next Service Due: {self.next_service}")
            
        return "\n".join(parts)


class VehicleService:
    """Service for vehicle management.
    
    Handles:
    - Vehicle CRUD operations
    - Vehicle configuration loading
    - RAG context assembly
    """
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path("config/vehicles")
        self._configs: dict[str, VehicleConfig] = {}
    
    def load_vehicle_config(self, vehicle_type: str) -> VehicleConfig:
        """Load vehicle configuration from YAML file.
        
        Args:
            vehicle_type: Vehicle type code (e.g., 'fzj80')
            
        Returns:
            Parsed vehicle configuration
        """
        if vehicle_type in self._configs:
            return self._configs[vehicle_type]
            
        config_path = self.config_dir / f"{vehicle_type}.yaml"
        
        if not config_path.exists():
            raise ValueError(f"No configuration found for vehicle type: {vehicle_type}")
            
        with open(config_path) as f:
            data = yaml.safe_load(f)
            
        config = VehicleConfig(
            vehicle_type=data["vehicle_type"],
            name=data["name"],
            production_years=data["production_years"],
            engine=data.get("engine", {}),
            transmission=data.get("transmission", {}),
            common_issues=data.get("common_issues", []),
            modifications=data.get("modifications", {}),
            knowledge_sources=data.get("knowledge_sources", {})
        )
        
        self._configs[vehicle_type] = config
        return config
    
    def get_supported_vehicles(self) -> list[dict]:
        """Get list of supported vehicle types."""
        vehicles = []
        
        for config_file in self.config_dir.glob("*.yaml"):
            try:
                with open(config_file) as f:
                    data = yaml.safe_load(f)
                    vehicles.append({
                        "type": data["vehicle_type"],
                        "name": data["name"],
                        "years": data["production_years"]
                    })
            except Exception as e:
                logger.warning(f"Failed to load {config_file}: {e}")
                
        return vehicles
    
    def get_rag_context(
        self,
        vehicle_type: str,
        vehicle_id: Optional[int] = None,
        nickname: Optional[str] = None,
        year: Optional[int] = None,
        current_mileage: Optional[int] = None,
    ) -> VehicleRAGContext:
        """Assemble vehicle context for RAG injection.
        
        Args:
            vehicle_type: Vehicle type code
            vehicle_id: Optional database vehicle ID
            nickname: Optional vehicle nickname
            year: Optional specific year
            current_mileage: Optional current mileage
            
        Returns:
            Vehicle context for RAG prompt
        """
        config = self.load_vehicle_config(vehicle_type)
        
        # TODO: If vehicle_id provided, load from database
        # - Get vehicle details
        # - Get recent services
        # - Get active modifications
        # - Calculate next due service
        
        return VehicleRAGContext(
            vehicle_type=vehicle_type,
            vehicle_name=config.name,
            year=year,
            nickname=nickname,
            current_mileage=current_mileage,
            engine_code=config.engine.get("code", "Unknown"),
            modifications=[],  # TODO: Load from database
            recent_services=[],  # TODO: Load from database
            next_service=None,  # TODO: Calculate from service records
        )
    
    def get_maintenance_schedule(self, vehicle_type: str) -> list[dict]:
        """Get maintenance schedule for a vehicle type."""
        config = self.load_vehicle_config(vehicle_type)
        
        schedules = []
        
        # Extract from engine maintenance
        engine_maint = config.engine.get("maintenance", {})
        
        if "oil_change" in engine_maint:
            schedules.append({
                "service_type": "oil_change",
                "interval_miles": engine_maint["oil_change"].get("interval_miles", 5000),
                "interval_months": engine_maint["oil_change"].get("interval_months", 6),
                "description": "Engine oil and filter change"
            })
            
        if "timing_belt" in engine_maint:
            schedules.append({
                "service_type": "timing_belt",
                "interval_miles": engine_maint["timing_belt"].get("interval_miles", 90000),
                "description": "Replace timing belt and water pump"
            })
            
        # Add more schedules from config...
        
        return schedules
