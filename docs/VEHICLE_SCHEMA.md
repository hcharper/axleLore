# RigSherpa Vehicle Schema

## Overview

This document defines the vehicle configuration schema used across RigSherpa. The schema enables multi-vehicle support while maintaining vehicle-specific accuracy.

---

## Vehicle Type Configuration

Each supported vehicle type has a configuration file in `config/vehicles/`.

### FZJ80 Configuration (MVP)

```yaml
# config/vehicles/fzj80.yaml
---
# Vehicle Identification
vehicle_type: fzj80
name: "Toyota Land Cruiser FZJ80"
manufacturer: toyota
platform: "80-series"
production_years: [1993, 1994, 1995, 1996, 1997]
markets: [us, canada, middle_east, australia]

# VIN Patterns
vin_patterns:
  - regex: "JT3DJ81W.*"
    description: "US Market FZJ80"
  - regex: "JT3HJ81W.*"
    description: "US Market FZJ80 (variant)"

# Engine Configuration
engine:
  code: "1FZ-FE"
  type: "inline-6"
  displacement_cc: 4477
  displacement_l: 4.5
  fuel_type: "gasoline"
  fuel_system: "EFI"
  horsepower: 212
  torque_lb_ft: 275
  compression_ratio: "9.0:1"
  firing_order: "1-5-3-6-2-4"
  
  fluids:
    oil:
      capacity_with_filter_qt: 6.8
      capacity_without_filter_qt: 6.1
      recommended_viscosity: ["5W-30", "10W-30"]
      filter_part_number: "90915-YZZB6"
    coolant:
      capacity_qt: 15.1
      type: "Toyota Red (SLLC)"
      
  maintenance:
    oil_change:
      interval_miles: 5000
      interval_months: 6
      severe_interval_miles: 3000
    timing_belt:
      interval_miles: 90000
      interference: false
    spark_plugs:
      interval_miles: 30000
      part_number: "90919-01178"
      gap_mm: 1.1

# Transmission Configuration  
transmission:
  automatic:
    code: "A442F"
    type: "4-speed automatic"
    fluid_capacity_qt: 10.4
    fluid_type: "Dexron III"
    filter_part_number: "35330-60050"
  manual:
    code: "R151F"
    type: "5-speed manual"
    fluid_capacity_qt: 2.2
    fluid_type: "GL-4 75W-90"

# Transfer Case
transfer_case:
  code: "HF2AV"
  type: "part-time/full-time 4WD"
  has_center_diff: true
  has_center_locker: true
  fluid_capacity_qt: 1.5
  fluid_type: "GL-5 80W-90"

# Axles
axles:
  front:
    type: "solid with birfield joints"
    diff_capacity_qt: 2.6
    diff_type: "open or optional ARB locker"
    fluid_type: "GL-5 80W-90"
    has_free_wheeling_hubs: false  # Full-time 4WD
  rear:
    type: "solid"
    diff_capacity_qt: 3.2
    diff_type: "open, limited-slip, or locker"
    fluid_type: "GL-5 80W-90"
    
# Brakes
brakes:
  front:
    type: "ventilated disc"
    rotor_diameter_mm: 310
    pad_thickness_min_mm: 1.0
  rear:
    type: "drum"
    drum_diameter_mm: 295
    shoe_thickness_min_mm: 1.0
  abs: true
  abs_module: "Bosch 5.3"

# Suspension
suspension:
  front:
    type: "coil spring, solid axle"
    spring_rate_lbs_in: 150
  rear:
    type: "coil spring, solid axle"  
    spring_rate_lbs_in: 200
  sway_bars:
    front: true
    rear: false

# Electrical
electrical:
  battery:
    group: "27F"
    cca: 650
    location: "engine bay, driver side"
  alternator:
    output_amps: 80
  ecu:
    type: "OBD-I (pre-1996), OBD-II (1996+)"
    connector: "Toyota 16-pin / OBD-II"

# Dimensions & Capacities
dimensions:
  wheelbase_in: 112.2
  length_in: 189.0
  width_in: 76.0
  height_in: 73.0
  ground_clearance_in: 8.7
  
weights:
  curb_weight_lbs: 4850
  gvwr_lbs: 6250
  towing_capacity_lbs: 5000

capacities:
  fuel_tank_gal: 25.1
  cargo_volume_cu_ft: 90

# Tire Information
tires:
  oem_size: "275/70R16"
  alternatives:
    - "285/75R16"
    - "315/75R16"  # Requires lift
    - "33x10.50R15"
  rotation_interval_miles: 7500
  pressure_front_psi: 29
  pressure_rear_psi: 29

# Common Issues (vehicle-specific)
common_issues:
  - code: "HEAD_GASKET"
    description: "Head gasket failure, especially vehicles with cooling system neglect"
    symptoms: ["overheating", "coolant loss", "white exhaust smoke"]
    affected_years: [1993, 1994, 1995, 1996, 1997]
    severity: "high"
    typical_cost_range: [2000, 4000]
    
  - code: "BIRFIELD_WEAR"
    description: "CV joint (birfield) wear at high mileage"
    symptoms: ["clicking when turning", "torn boot"]
    affected_years: [1993, 1994, 1995, 1996, 1997]
    severity: "medium"
    typical_cost_range: [500, 1500]
    
  - code: "CHARCOAL_CANISTER"
    description: "Evaporative emissions charcoal canister failure"
    symptoms: ["fuel smell", "check engine light", "hard starting when hot"]
    affected_years: [1993, 1994, 1995]
    severity: "low"
    typical_cost_range: [200, 400]

  - code: "FRAME_RUST"
    description: "Frame rust in rust belt vehicles"
    symptoms: ["visible rust", "structural compromise"]
    affected_years: [1993, 1994, 1995, 1996, 1997]
    severity: "critical"
    regions: ["northeast_us", "midwest_us"]
    
# Popular Modifications
modifications:
  suspension:
    - name: "OME Heavy Duty"
      type: "2.5\" lift"
      part_numbers: ["2861", "2863"]
      notes: "Most popular option, good for daily/overland"
      
    - name: "Icon Stage 2"
      type: "3\" lift"
      notes: "Premium option, great ride quality"
      
  armor:
    - name: "SOR Rock Sliders"
      notes: "Bolt-on protection"
      
    - name: "Slee Off Road Bumper"
      notes: "Front bumper with winch mount"
      
  drivetrain:
    - name: "ARB Air Locker"
      location: ["front", "rear"]
      notes: "Selectable locker, most popular option"
      
    - name: "Detroit Locker"
      location: ["rear"]
      notes: "Automatic locker, best for dedicated off-road"

# Knowledge Sources
knowledge_sources:
  fsm:
    volumes: ["engine", "chassis", "body", "ewd"]
    years_covered: [1993, 1994, 1995, 1996, 1997]
    
  forums:
    - name: "IH8MUD"
      url: "https://forum.ih8mud.com/"
      sections: ["80-Series Tech", "Newbie Tech"]
      quality: "excellent"
      
    - name: "LandCruiserWorld"  
      url: "https://landcruiserworld.com/"
      quality: "good"
      
  vendors:
    - name: "SOR (Specter Off-Road)"
      url: "https://sor.com/"
      specialty: ["parts", "accessories"]
      
    - name: "Cruiser Corps"
      specialty: ["used parts"]
      
    - name: "Toyota Dealer"
      specialty: ["OEM parts"]

# Related Vehicles (for shared knowledge)
related_vehicles:
  - vehicle_type: "fj80"
    relationship: "same platform, different engine"
    shared_systems: ["axles", "body", "suspension", "steering"]
    
  - vehicle_type: "lx450"
    relationship: "Lexus variant"
    shared_systems: ["drivetrain", "chassis"]
```

---

## User Vehicle Instance

Each user's actual vehicle is stored as an instance with the vehicle type as base.

### Database Schema

```python
# Already in src/backend/models/database.py
class Vehicle(Base):
    """User's specific vehicle."""
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True)
    vehicle_type = Column(String(50), nullable=False)  # References config
    nickname = Column(String(100))  # "Betsy"
    year = Column(Integer)  # 1995
    vin = Column(String(17))
    current_mileage = Column(Integer)
    purchase_date = Column(DateTime)
    purchase_mileage = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### API Schema

```python
# src/backend/models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

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
    
class VehicleRead(VehicleBase):
    """Schema for reading vehicle."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    # Computed from vehicle type config
    display_name: str  # "1995 Toyota Land Cruiser FZJ80"
    engine_code: str
    
    class Config:
        from_attributes = True

class VehicleWithContext(VehicleRead):
    """Vehicle with service/mod context for RAG."""
    service_summary: dict  # Recent services, next due
    modifications: List[str]  # Active modifications
    known_issues: List[str]  # Active issues/concerns
    total_services: int
    last_service_date: Optional[datetime]
    last_service_mileage: Optional[int]
```

---

## Service Records

### Database Schema

```python
class ServiceRecord(Base):
    """Service record model."""
    __tablename__ = "service_records"
    
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    
    # Service Details
    service_date = Column(DateTime, nullable=False)
    mileage = Column(Integer)
    service_type = Column(String(50))  # Uses ServiceType enum
    description = Column(Text)
    
    # Cost & Parts
    cost = Column(Float)
    parts_used = Column(JSON)  # [{"part_number": "...", "name": "...", "qty": 1}]
    
    # Who/Where
    performed_by = Column(String(100))  # "self", "Toyota Dealer", etc.
    location = Column(String(200))
    
    # Next Service
    next_service_mileage = Column(Integer)
    next_service_date = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
```

### Service Types

```python
from enum import Enum

class ServiceType(str, Enum):
    """Standardized service types."""
    
    # Routine Maintenance
    OIL_CHANGE = "oil_change"
    TIRE_ROTATION = "tire_rotation"
    AIR_FILTER = "air_filter"
    CABIN_FILTER = "cabin_filter"
    BRAKE_INSPECTION = "brake_inspection"
    FLUID_CHECK = "fluid_check"
    
    # Major Service
    TIMING_BELT = "timing_belt"
    SPARK_PLUGS = "spark_plugs"
    TRANSMISSION_SERVICE = "transmission_service"
    DIFF_SERVICE = "diff_service"
    COOLANT_FLUSH = "coolant_flush"
    BRAKE_FLUID_FLUSH = "brake_fluid_flush"
    POWER_STEERING_FLUSH = "power_steering_flush"
    
    # Repairs
    BRAKE_PADS = "brake_pads"
    BRAKE_ROTORS = "brake_rotors"
    SUSPENSION = "suspension"
    STEERING = "steering"
    ELECTRICAL = "electrical"
    ENGINE_REPAIR = "engine_repair"
    TRANSMISSION_REPAIR = "transmission_repair"
    AXLE_REPAIR = "axle_repair"
    EXHAUST = "exhaust"
    COOLING = "cooling"
    FUEL_SYSTEM = "fuel_system"
    
    # Modifications
    LIFT_INSTALL = "lift_install"
    LOCKER_INSTALL = "locker_install"
    BUMPER_INSTALL = "bumper_install"
    LIGHTING = "lighting"
    ACCESSORY = "accessory"
    
    # Inspections
    PRE_PURCHASE = "pre_purchase"
    ANNUAL_INSPECTION = "annual_inspection"
    EMISSIONS = "emissions"
    
    # Other
    OTHER = "other"
```

### API Schema

```python
class ServiceRecordCreate(BaseModel):
    """Create service record."""
    service_date: datetime
    service_type: ServiceType
    mileage: Optional[int]
    description: Optional[str]
    cost: Optional[float]
    parts_used: Optional[List[PartUsed]]
    performed_by: Optional[str] = "self"
    location: Optional[str]
    next_service_mileage: Optional[int]
    next_service_date: Optional[datetime]
    notes: Optional[str]

class PartUsed(BaseModel):
    """Part used in service."""
    part_number: Optional[str]
    name: str
    quantity: int = 1
    cost: Optional[float]
    brand: Optional[str]

class ServiceRecordRead(ServiceRecordCreate):
    """Read service record."""
    id: int
    vehicle_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
```

---

## Modifications Tracking

```python
class VehicleModification(Base):
    """Track vehicle modifications."""
    __tablename__ = "vehicle_modifications"
    
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    
    # Modification Details
    name = Column(String(200), nullable=False)
    category = Column(String(50))  # suspension, armor, electrical, etc.
    install_date = Column(DateTime)
    install_mileage = Column(Integer)
    
    # Products Used
    brand = Column(String(100))
    part_number = Column(String(100))
    
    # Status
    is_active = Column(Boolean, default=True)
    removed_date = Column(DateTime)
    
    # Notes
    notes = Column(Text)
    impacts = Column(JSON)  # {"ground_clearance": "+2.5in", "fuel_economy": "-1mpg"}
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Modification Categories

```python
class ModificationCategory(str, Enum):
    """Modification categories."""
    
    SUSPENSION = "suspension"  # Lifts, springs, shocks
    ARMOR = "armor"  # Sliders, skids, bumpers
    DRIVETRAIN = "drivetrain"  # Lockers, gears, driveshafts
    WHEELS_TIRES = "wheels_tires"
    LIGHTING = "lighting"
    ELECTRICAL = "electrical"
    INTAKE_EXHAUST = "intake_exhaust"
    RECOVERY = "recovery"  # Winch, recovery points
    STORAGE = "storage"  # Racks, drawers
    COMFORT = "comfort"  # Interior mods
    OTHER = "other"
```

---

## Context Assembly for RAG

The vehicle context is assembled and injected into every RAG query:

```python
# src/backend/services/vehicle.py
class VehicleService:
    """Vehicle management and context assembly."""
    
    def get_rag_context(self, vehicle_id: int) -> VehicleRAGContext:
        """Assemble full context for RAG injection."""
        vehicle = self.get_vehicle(vehicle_id)
        config = self.load_vehicle_config(vehicle.vehicle_type)
        services = self.get_recent_services(vehicle_id, limit=10)
        mods = self.get_active_modifications(vehicle_id)
        
        return VehicleRAGContext(
            vehicle_type=vehicle.vehicle_type,
            vehicle_name=config.name,
            year=vehicle.year,
            nickname=vehicle.nickname,
            current_mileage=vehicle.current_mileage,
            engine=config.engine,
            modifications=[m.name for m in mods],
            recent_services=[
                f"{s.service_date.date()}: {s.service_type} @ {s.mileage}mi"
                for s in services
            ],
            next_service=self.get_next_due_service(vehicle_id),
            known_issues=self.get_active_issues(vehicle_id),
        )

class VehicleRAGContext(BaseModel):
    """Context injected into RAG prompts."""
    vehicle_type: str
    vehicle_name: str
    year: Optional[int]
    nickname: Optional[str]
    current_mileage: Optional[int]
    engine: dict
    modifications: List[str]
    recent_services: List[str]
    next_service: Optional[dict]
    known_issues: List[str]
    
    def to_prompt_string(self) -> str:
        """Format for system prompt injection."""
        parts = [
            f"Vehicle: {self.year or ''} {self.vehicle_name}",
            f"Nickname: {self.nickname}" if self.nickname else None,
            f"Current Mileage: {self.current_mileage:,}" if self.current_mileage else None,
            f"Engine: {self.engine.get('code')} ({self.engine.get('displacement_l')}L)",
        ]
        
        if self.modifications:
            parts.append(f"Modifications: {', '.join(self.modifications)}")
            
        if self.recent_services:
            parts.append("Recent Services:")
            parts.extend([f"  - {s}" for s in self.recent_services[:5]])
            
        if self.next_service:
            parts.append(f"Next Service Due: {self.next_service}")
            
        return "\n".join(filter(None, parts))
```

---

## Vehicle Expansion Template

When adding a new vehicle type:

1. Create `config/vehicles/{vehicle_type}.yaml`
2. Collect knowledge sources:
   - FSM/Service Manual
   - Forum data
   - Parts catalogs
   - TSBs
3. Run data pipeline for new vehicle
4. Test with vehicle-specific queries
5. Update UI vehicle selector

### Minimal Vehicle Config

```yaml
# config/vehicles/template.yaml
---
vehicle_type: "{code}"
name: "{Full Vehicle Name}"
manufacturer: "{manufacturer}"
production_years: []

engine:
  code: ""
  fluids:
    oil:
      capacity_with_filter_qt: 0
      recommended_viscosity: []

transmission:
  automatic:
    code: ""
    fluid_capacity_qt: 0
    fluid_type: ""

# Fill in as knowledge is gathered
tire:
  oem_size: ""

common_issues: []
modifications: []
knowledge_sources: []
related_vehicles: []
```
