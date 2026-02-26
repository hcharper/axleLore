# RigSherpa System Architecture

## Overview

RigSherpa follows a modular, layered architecture designed for resource-constrained environments (Raspberry Pi) while maintaining extensibility for future features.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACES                                │
├─────────────────┬─────────────────┬─────────────────┬───────────────────┤
│   Web UI        │   CLI           │   Voice (v2)    │   Mobile (v3)     │
│   (Svelte)      │   (Click)       │   (Whisper)     │   (React Native)  │
└────────┬────────┴────────┬────────┴────────┬────────┴─────────┬─────────┘
         │                 │                 │                  │
         └─────────────────┴─────────────────┴──────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (FastAPI)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  /chat      │  │  /vehicle   │  │  /service   │  │  /obd2      │     │
│  │  endpoints  │  │  endpoints  │  │  endpoints  │  │  endpoints  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           CORE SERVICES                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │  ChatService     │  │  VehicleService  │  │  OBD2Service     │       │
│  │  - Query LLM     │  │  - CRUD vehicles │  │  - Connect/read  │       │
│  │  - Context mgmt  │  │  - Service logs  │  │  - DTC decode    │       │
│  │  - Chat history  │  │  - Modifications │  │  - Data logging  │       │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           RAG PIPELINE                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Query → Embed → Vector Search → Context Assembly → LLM → Response│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Embedder   │  │  Retriever  │  │  Reranker   │  │  Generator  │     │
│  │  MiniLM-L6  │  │  ChromaDB   │  │  (optional) │  │  Ollama     │     │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│    Vector Store     │ │   SQL Database  │ │    File Storage     │
│    (ChromaDB)       │ │   (SQLite)      │ │    (Local FS)       │
│ ┌─────────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────────┐ │
│ │ FSM chunks      │ │ │ │ vehicles    │ │ │ │ /data/vehicles/ │ │
│ │ Forum posts     │ │ │ │ services    │ │ │ │ /data/logs/     │ │
│ │ Part numbers    │ │ │ │ obd2_data   │ │ │ │ /data/db/       │ │
│ │ Procedures      │ │ │ │ chat_history│ │ │ │ /config/        │ │
│ └─────────────────┘ │ │ └─────────────┘ │ │ └─────────────────┘ │
└─────────────────────┘ └─────────────────┘ └─────────────────────┘
```

## Component Details

### 1. API Layer (FastAPI)

**Purpose**: RESTful API gateway handling all client requests

**Endpoints**:
```
/api/v1/
├── chat/
│   ├── POST /message          # Send message to LLM
│   ├── GET /history           # Get chat history
│   └── DELETE /history        # Clear history
├── vehicles/
│   ├── GET /                  # List vehicles
│   ├── POST /                 # Add vehicle  
│   ├── GET /{id}              # Get vehicle details
│   ├── PUT /{id}              # Update vehicle
│   └── DELETE /{id}           # Delete vehicle
├── service/
│   ├── GET /{vehicle_id}/records      # List service records
│   ├── POST /{vehicle_id}/records     # Add service record
│   └── GET /schedules/{vehicle_type}  # Get maintenance schedule
├── obd2/
│   ├── GET /status            # Connection status
│   ├── POST /connect          # Connect to OBD2
│   ├── GET /live              # Live data stream (WebSocket)
│   ├── GET /dtc               # Read DTCs
│   └── POST /clear-dtc        # Clear DTCs
└── knowledge/
    ├── GET /search            # Search knowledge base
    ├── GET /parts/{query}     # Part number lookup
    └── GET /procedures/{id}   # Get procedure details
```

### 2. RAG Pipeline

The Retrieval-Augmented Generation pipeline is the core intelligence layer.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RAG PIPELINE FLOW                                │
│                                                                          │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐                  │
│  │  User    │    │  Query       │    │   Context     │                  │
│  │  Query   │───▶│  Processing  │───▶│   Retrieval   │                  │
│  └──────────┘    └──────────────┘    └───────────────┘                  │
│                        │                     │                           │
│                        ▼                     ▼                           │
│               ┌──────────────┐    ┌───────────────────┐                 │
│               │ Vehicle      │    │ Knowledge Sources │                 │
│               │ Context      │    │ - FSM chunks      │                 │
│               │ Injection    │    │ - Forum posts     │                 │
│               └──────────────┘    │ - Service history │                 │
│                        │          └───────────────────┘                 │
│                        ▼                     │                           │
│               ┌──────────────────────────────┘                          │
│               │                                                          │
│               ▼                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐   │
│  │  Prompt          │    │  LLM             │    │  Response        │   │
│  │  Assembly        │───▶│  Generation      │───▶│  Post-Process    │   │
│  │  (System+User)   │    │  (Ollama/Qwen3) │    │  (Citations)     │   │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘   │
│                                                           │              │
│                                                           ▼              │
│                                                    ┌──────────────┐     │
│                                                    │   Response   │     │
│                                                    └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

**Query Processing**:
1. Extract intent (question type, urgency)
2. Identify vehicle-specific keywords
3. Detect part numbers, DTCs, or procedures

**Context Retrieval**:
1. Generate embeddings for query
2. Search ChromaDB with filters (vehicle_type, category)
3. Retrieve top-k similar chunks
4. Optionally rerank results

**Prompt Assembly**:
```python
SYSTEM_PROMPT = """You are RigSherpa, an expert automotive assistant 
specializing in the {vehicle_type}. You have access to:
- Factory Service Manual (FSM)
- Technical Service Bulletins (TSBs)
- Enthusiast forum knowledge from IH8MUD and related communities
- This vehicle's service history and modifications

Current Vehicle: {vehicle_nickname} ({vehicle_year} {vehicle_type})
Mileage: {current_mileage}
Known Modifications: {modifications}

Guidelines:
- Be specific and technical when appropriate
- Cite sources when possible (FSM page, forum thread)
- If unsure, say so - don't guess on safety-critical items
- Include part numbers when relevant
- Consider the user's skill level based on conversation

Context from knowledge base:
{retrieved_context}
"""
```

### 3. Vector Store (ChromaDB)

**Collections**:
```
chromadb/
├── fsm_{vehicle_type}/        # Factory Service Manual chunks
│   metadata: {page, section, category, procedure_id}
├── forum_{vehicle_type}/      # Forum post chunks  
│   metadata: {source, thread_id, author, date, votes}
├── parts_{vehicle_type}/      # Part numbers and specs
│   metadata: {part_number, oem_number, category}
└── procedures_{vehicle_type}/ # Step-by-step procedures
    metadata: {difficulty, tools, time_estimate, category}
```

**Document Categories**:
- `engine`: Engine-related (1FZ-FE specific)
- `transmission`: A442F, A440F
- `electrical`: Wiring, sensors, ECU
- `axles`: Front/rear axle, diffs, birfields
- `suspension`: Springs, shocks, lifts
- `brakes`: Pads, rotors, ABS
- `body`: Interior, exterior, rust
- `cooling`: Radiator, heater core
- `fuel`: Fuel system, injection
- `exhaust`: Headers, catalytic converters
- `steering`: Power steering, knuckles
- `modifications`: Aftermarket installs

### 4. OBD2 Integration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         OBD2 INTEGRATION                                 │
│                                                                          │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐                  │
│  │  ELM327  │    │  python-OBD  │    │  OBD2Service  │                  │
│  │  Adapter │───▶│  Library     │───▶│  (FastAPI)    │                  │
│  └──────────┘    └──────────────┘    └───────────────┘                  │
│       │                                      │                           │
│       │                                      ▼                           │
│       │                         ┌───────────────────────┐               │
│       │                         │  Live Data Stream     │               │
│       │                         │  - RPM, Speed, Temp   │               │
│       │                         │  - Fuel trims         │               │
│       │                         │  - O2 sensors         │               │
│       │                         └───────────────────────┘               │
│       │                                      │                           │
│       │                                      ▼                           │
│       │                         ┌───────────────────────┐               │
│       │                         │  DTC Management       │               │
│       │                         │  - Read codes         │               │
│       │                         │  - Clear codes        │               │
│       │                         │  - Freeze frame       │               │
│       │                         └───────────────────────┘               │
│       │                                      │                           │
│       │                                      ▼                           │
│       │                         ┌───────────────────────┐               │
│       │                         │  AI Integration       │               │
│       │                         │  - DTC explanation    │               │
│       │                         │  - Fix suggestions    │               │
│       │                         │  - Pattern detection  │               │
│       │                         └───────────────────────┘               │
│       │                                                                  │
└───────┴──────────────────────────────────────────────────────────────────┘
```

**Supported PIDs** (Phase 2):
- Engine RPM, Speed, Coolant Temp
- Throttle Position
- MAF Sensor
- Fuel System Status
- Short/Long Term Fuel Trim
- O2 Sensor Voltages
- Intake Air Temp
- Engine Load

### 5. Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    OFFLINE DATA PIPELINE (Build Time)                    │
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │  Scrapers   │    │ Processors  │    │ KB Builder  │                  │
│  │  - IH8MUD   │───▶│ - Clean     │───▶│ - Chunk     │                  │
│  │  - FSM PDFs │    │ - Extract   │    │ - Embed     │                  │
│  │  - Parts    │    │ - Normalize │    │ - Index     │                  │
│  └─────────────┘    └─────────────┘    └─────────────┘                  │
│                                               │                          │
│                                               ▼                          │
│                                    ┌─────────────────────┐              │
│                                    │  Vehicle Pack       │              │
│                                    │  (Distributable)    │              │
│                                    │  - ChromaDB export  │              │
│                                    │  - Metadata         │              │
│                                    └─────────────────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      RUNTIME DATA FLOW                                   │
│                                                                          │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐        │
│  │   User      │         │   RigSherpa  │         │  Knowledge  │        │
│  │   Query     │────────▶│   Backend   │────────▶│   Base      │        │
│  └─────────────┘         └─────────────┘         └─────────────┘        │
│        │                       │                        │                │
│        │                       ▼                        │                │
│        │              ┌─────────────────┐               │                │
│        │              │  RAG Pipeline   │◀──────────────┘                │
│        │              └─────────────────┘                                │
│        │                       │                                         │
│        │                       ▼                                         │
│        │              ┌─────────────────┐                                │
│        │              │  Ollama (LLM)   │                                │
│        │              └─────────────────┘                                │
│        │                       │                                         │
│        ◀───────────────────────┘                                         │
│   Response                                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
rigsherpa/
├── pyproject.toml              # Project configuration
├── requirements.txt            # Dependencies (generated)
├── README.md                   # Quick start guide
├── .env.example                # Environment template
│
├── bin/                        # Shell scripts
│   ├── install.sh              # Installation script
│   ├── start.sh                # Start services
│   └── update.sh               # Update knowledge base
│
├── config/                     # Configuration files
│   ├── vehicles/               # Vehicle-specific configs
│   │   ├── fzj80.yaml          # FZJ80 configuration
│   │   └── fj80.yaml           # FJ80 configuration
│   ├── ollama.yaml             # Ollama model configs
│   └── logging.yaml            # Logging configuration
│
├── data/                       # Runtime data (gitignored)
│   ├── db/                     # SQLite databases
│   │   └── rigsherpa.db
│   ├── chromadb/               # Vector store
│   ├── logs/                   # Application logs
│   │   ├── chat/               # Chat logs
│   │   └── obd2/               # OBD2 session logs
│   └── vehicles/               # User vehicle data
│
├── docs/                       # Documentation
│   ├── README.md               # Project overview
│   ├── ARCHITECTURE.md         # This file
│   ├── MVP_ROADMAP.md          # Development roadmap
│   ├── DATA_PIPELINE.md        # Data collection guide
│   └── API.md                  # API documentation
│
├── src/                        # Source code
│   ├── backend/                # FastAPI backend
│   │   ├── __init__.py
│   │   ├── main.py             # Application entry
│   │   ├── api/                # API routes
│   │   │   ├── __init__.py
│   │   │   ├── chat.py         # Chat endpoints
│   │   │   ├── vehicles.py     # Vehicle endpoints
│   │   │   ├── service.py      # Service record endpoints
│   │   │   ├── obd2.py         # OBD2 endpoints
│   │   │   └── knowledge.py    # Knowledge base endpoints
│   │   ├── core/               # Core configuration
│   │   │   ├── __init__.py
│   │   │   ├── config.py       # Settings management
│   │   │   └── dependencies.py # FastAPI dependencies
│   │   ├── models/             # Database models
│   │   │   ├── __init__.py
│   │   │   ├── database.py     # SQLAlchemy models
│   │   │   └── schemas.py      # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── chat.py         # Chat/LLM service
│   │   │   ├── vehicle.py      # Vehicle management
│   │   │   ├── rag.py          # RAG pipeline
│   │   │   ├── obd2.py         # OBD2 service
│   │   │   └── knowledge.py    # Knowledge base service
│   │   └── utils/              # Utilities
│   │       ├── __init__.py
│   │       ├── embeddings.py   # Embedding utilities
│   │       └── prompts.py      # Prompt templates
│   │
│   ├── frontend/               # Web UI (Svelte or React)
│   │   └── ...
│   │
│   └── scripts/                # Deployment scripts
│       └── systemd/            # Systemd service files
│
├── tools/                      # Build-time tools
│   ├── kb_builder/             # Knowledge base builder
│   │   ├── __init__.py
│   │   ├── builder.py          # Main builder
│   │   ├── chunker.py          # Document chunking
│   │   └── embedder.py         # Embedding generation
│   ├── processors/             # Data processors
│   │   ├── __init__.py
│   │   ├── forum.py            # Forum post processor
│   │   ├── fsm.py              # FSM PDF processor
│   │   └── parts.py            # Parts catalog processor
│   └── scrapers/               # Web scrapers
│       ├── __init__.py
│       ├── ih8mud.py           # IH8MUD scraper
│       └── base.py             # Base scraper class
│
└── tests/                      # Test suite
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures
    ├── test_api/               # API tests
    ├── test_services/          # Service tests
    └── test_rag/               # RAG pipeline tests
```

## Hardware Requirements

### Minimum (Raspberry Pi 5, 8GB)
- CPU: ARM Cortex-A76 @ 2.4GHz (4 cores)
- RAM: 8GB
- Storage: 64GB microSD (Class 10) or NVMe
- OS: Raspberry Pi OS 64-bit (Bookworm)

### Recommended (Desktop-class)
- CPU: Any modern x86_64 or ARM64
- RAM: 16GB+
- Storage: 256GB SSD
- GPU: Optional (for faster inference)

### Performance Expectations (Pi 5)
- First token: ~2-3 seconds
- Token generation: ~10-15 tokens/second
- Embedding generation: ~100ms per query
- Vector search: <50ms

## Security Considerations

1. **Local-First**: No data leaves the device by default
2. **No Auth Required**: Single-user device assumption
3. **Optional Encryption**: Service records can be encrypted
4. **OBD2 Safety**: Read-only by default, write operations require confirmation
5. **Update Integrity**: Signed knowledge pack updates

## Scalability Path

1. **Single Vehicle** → Multiple vehicles per device
2. **Offline Only** → Optional cloud sync
3. **Consumer** → Fleet management (commercial)
4. **Manual Entry** → Automatic service detection via OBD2
