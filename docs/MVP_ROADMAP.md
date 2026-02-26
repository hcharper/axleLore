# RigSherpa MVP Roadmap

## Overview

This roadmap outlines the development path from initial prototype to market-ready product. The MVP focuses exclusively on the **Toyota FZJ80 Land Cruiser** as the inaugural vehicle.

## Timeline Summary

| Phase | Duration | Goal |
|-------|----------|------|
| Phase 0: Foundation | 2 weeks | Project setup, tooling, basic backend |
| Phase 1: Data Pipeline | 3 weeks | Scraping, processing, knowledge base |
| Phase 2: RAG Core | 2 weeks | Working Q&A system |
| Phase 3: Vehicle Features | 2 weeks | Service records, vehicle context |
| Phase 4: UI & Polish | 2 weeks | Web interface, UX refinement |
| Phase 5: Hardware | 2 weeks | Pi deployment, packaging |
| **Total MVP** | **~13 weeks** | Market-ready FZJ80 product |

---

## Phase 0: Foundation (Weeks 1-2) ✅ COMPLETED

### Goals
- Project structure and tooling
- Development environment
- Basic API skeleton

### Tasks

#### 0.1 Project Setup ✅
- [x] Initialize repository
- [x] Set up pyproject.toml
- [x] Configure linting (ruff, black, mypy)
- [x] Create directory structure
- [x] Write documentation structure

#### 0.2 Development Environment
- [ ] Docker Compose for development
- [ ] Pre-commit hooks
- [ ] GitHub Actions CI/CD
- [ ] Environment configuration (.env)

#### 0.3 Backend Skeleton ✅
- [x] FastAPI application structure
- [x] Configuration management (Pydantic Settings)
- [x] Database models (SQLAlchemy)
- [x] Health check endpoint
- [ ] Basic logging setup

#### 0.4 Ollama Integration ✅
- [x] Ollama installation script
- [x] Model download script (qwen3:1.7b)
- [x] Basic Ollama client wrapper
- [x] Connection health check

### Deliverables
- Working FastAPI server
- Ollama running with Qwen3 1.7B model
- Development environment documented

---

## Phase 1: Data Pipeline (Weeks 3-5) ✅ COMPLETED

### Goals
- Collect FZJ80 knowledge from multiple sources
- Process and normalize data
- Build initial knowledge base

### Tasks

#### 1.1 FSM Processing
- [ ] Obtain FZJ80 Factory Service Manual PDFs (legal sources)
- [ ] PDF extraction pipeline (PyMuPDF)
- [ ] OCR for scanned pages (Tesseract)
- [ ] Section classification (engine, electrical, etc.)
- [ ] Chunk documents appropriately (800 tokens, 100 overlap)
- [ ] Extract procedure steps with images references

#### 1.2 Forum Scraping
- [ ] IH8MUD scraper (Scrapy)
  - [ ] 80 Series forum threads
  - [ ] Respect robots.txt and rate limits
  - [ ] Extract thread title, posts, votes, dates
- [ ] Handle pagination and archives
- [ ] Deduplicate content
- [ ] Quality filtering (upvoted posts, verified solutions)

#### 1.3 Parts Database
- [ ] Toyota OEM parts catalog extraction
- [ ] Rock Auto integration (aftermarket)
- [ ] Part number cross-reference
- [ ] Price ranges (optional)

#### 1.4 Knowledge Base Builder
- [ ] ChromaDB setup and configuration
- [ ] Embedding generation pipeline (all-MiniLM-L6-v2)
- [ ] Metadata tagging system
- [ ] Collection organization by category
- [ ] Export/import for distribution

### Deliverables
- 10,000+ quality document chunks
- Searchable knowledge base
- Reproducible build pipeline

### Data Targets (FZJ80)
| Source | Target Chunks | Categories |
|--------|---------------|------------|
| FSM | 5,000+ | All systems |
| IH8MUD | 4,000+ | Mods, repairs, troubleshooting |
| Parts | 1,000+ | Part numbers, specs |
| TSBs | 200+ | Known issues |

---

## Phase 2: RAG Core (Weeks 6-7)

### Goals
- Working question-answering system
- Vehicle-aware context injection
- Quality responses with citations

### Tasks

#### 2.1 Retrieval System
- [ ] Query preprocessing (intent detection)
- [ ] Embedding-based retrieval
- [ ] Metadata filtering (category, source)
- [ ] Relevance scoring
- [ ] Top-k selection with diversity

#### 2.2 Context Assembly
- [ ] Vehicle context injection
- [ ] Service history awareness
- [ ] Modification-aware prompts
- [ ] Source citation formatting

#### 2.3 LLM Integration
- [ ] Ollama async client
- [ ] Streaming response support
- [ ] System prompt engineering
- [ ] Response post-processing
- [ ] Hallucination mitigation

#### 2.4 Chat API
- [ ] POST /chat/message endpoint
- [ ] Chat history management
- [ ] Context window management
- [ ] Rate limiting (for shared use)

### Deliverables
- Working Q&A via API
- Response quality >80% satisfaction
- <5 second response time on Pi

### Example Interactions
```
User: "What's the torque spec for the front axle knuckle bolts?"
RigSherpa: "The front axle knuckle bolts (part #90105-12220) should be 
torqued to 80 ft-lbs (108 Nm) per the FSM. Apply blue threadlocker.
[Source: FSM Section AX-12, IH8MUD Birfield Rebuild Guide]"

User: "My truck is making a clicking noise when turning"
RigSherpa: "Clicking when turning on an FZJ80 is typically one of:
1. Worn CV joints/birfields (most common) - check for torn boots
2. Wheel bearing play - jack up and check for movement
3. Brake pad wear indicator

Based on your service records, you're at 185,000 miles with no birfield
service recorded. Recommend inspection. The OEM birfield rebuild is 
labor-intensive but well-documented. [Source: IH8MUD Birfield FAQ]"
```

---

## Phase 3: Vehicle Features (Weeks 8-9)

### Goals
- Full vehicle management
- Service record tracking
- Maintenance scheduling

### Tasks

#### 3.1 Vehicle Management
- [ ] CRUD API for vehicles
- [ ] Vehicle profile schema
- [ ] VIN decoding (optional)
- [ ] Multi-vehicle support

#### 3.2 Service Records
- [ ] Service record CRUD
- [ ] Service type taxonomy
- [ ] Parts used tracking
- [ ] Cost tracking
- [ ] Photo attachments (optional)

#### 3.3 Maintenance Scheduling
- [ ] FZJ80 maintenance schedule
- [ ] Mileage-based reminders
- [ ] Time-based reminders
- [ ] Overdue notifications

#### 3.4 Vehicle Context Integration
- [ ] Service history in RAG context
- [ ] Modification awareness
- [ ] Mileage-appropriate advice
- [ ] "My truck" pronouns

### Deliverables
- Complete vehicle management
- Service history tracking
- Context-aware responses

---

## Phase 4: UI & Polish (Weeks 10-11)

### Goals
- Functional web interface
- Mobile-responsive design
- Excellent UX

### Tasks

#### 4.1 Frontend Setup
- [ ] Choose framework (Svelte recommended for bundle size)
- [ ] Project scaffolding
- [ ] API client setup
- [ ] State management

#### 4.2 Chat Interface
- [ ] Chat message display
- [ ] Markdown rendering
- [ ] Code block formatting
- [ ] Source citations UI
- [ ] Typing indicators

#### 4.3 Vehicle Dashboard
- [ ] Vehicle selector
- [ ] Vehicle profile view
- [ ] Service record list
- [ ] Add service form
- [ ] Maintenance schedule view

#### 4.4 Settings & Configuration
- [ ] Vehicle setup wizard
- [ ] Model selection
- [ ] Theme (light/dark)
- [ ] Export/import data

#### 4.5 Polish
- [ ] Loading states
- [ ] Error handling
- [ ] Offline indicators
- [ ] Keyboard shortcuts
- [ ] Touch optimization

### Deliverables
- Complete web interface
- Mobile-responsive
- <500KB bundle size

### UI Wireframes

```
┌─────────────────────────────────────────────────────────────┐
│  🚙 RigSherpa              [FZJ80 "Betsy" ▼]    [⚙️]         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🤖 Welcome! I'm your FZJ80 assistant. How can I     │   │
│  │    help you today?                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 👤 What's the oil capacity for a 1FZ-FE?            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🤖 The 1FZ-FE engine oil capacity is:               │   │
│  │    • Without filter: 6.1 quarts (5.8L)              │   │
│  │    • With filter: 6.8 quarts (6.4L)                 │   │
│  │                                                      │   │
│  │    Toyota recommends 5W-30 or 10W-30 depending on   │   │
│  │    climate. [FSM Section LU-3]                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Type your question...                          [📤] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [💬 Chat] [📋 Service] [🔧 Parts] [📊 OBD2]              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 5: Hardware & Deployment (Weeks 12-13)

### Goals
- One-command installation
- Raspberry Pi optimization
- Distributable package

### Tasks

#### 5.1 Pi Optimization
- [ ] Memory optimization
- [ ] Swap configuration
- [ ] Model quantization verification
- [ ] Cold start optimization
- [ ] Background service setup

#### 5.2 Installation
- [ ] Installation script
- [ ] Dependency management
- [ ] Ollama auto-setup
- [ ] Model download
- [ ] Service configuration

#### 5.3 Systemd Services
- [ ] rigsherpa.service (FastAPI)
- [ ] ollama.service (if not system)
- [ ] Auto-start on boot
- [ ] Watchdog for reliability

#### 5.4 Packaging
- [ ] SD card image creation
- [ ] First-run wizard
- [ ] Network configuration
- [ ] Access point mode (optional)

#### 5.5 Documentation
- [ ] Installation guide
- [ ] User manual
- [ ] Troubleshooting guide
- [ ] API documentation

### Deliverables
- Flashable SD card image
- Installation script for existing Pi
- Complete documentation

### Performance Benchmarks (Target)

| Metric | Target | Acceptable |
|--------|--------|------------|
| Cold start | <60s | <90s |
| First response | <5s | <8s |
| Token rate | 10 tok/s | 7 tok/s |
| Memory usage | <6GB | <7GB |
| Storage (base) | <16GB | <24GB |

---

## Post-MVP Phases

### Phase 6: OBD2 Integration
- Live data display
- DTC reading and explanation
- Freeze frame analysis
- Trip logging

### Phase 7: Sales Platform
- Next.js marketing site
- Stripe integration
- Download delivery
- License key management

### Phase 8: Vehicle Expansion
- FJ80 (3F-E engine)
- 100 Series Land Cruiser
- 3rd Gen 4Runner

### Phase 9: Community Features
- Anonymous data sharing
- Community fix database
- Modification registry

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| FSM copyright issues | High | Medium | Use only legally obtained sources, cite properly |
| Forum scraping blocked | Medium | Low | Rate limiting, caching, manual review |
| Pi performance insufficient | High | Low | Smaller model, quantization, caching |
| Ollama instability | Medium | Low | Fallback to llama.cpp direct |
| Low quality responses | High | Medium | Extensive prompt engineering, RAG tuning |

---

## Success Metrics (MVP)

| Metric | Target |
|--------|--------|
| Response accuracy | >85% |
| User satisfaction | >4.0/5 |
| Response time | <5 seconds |
| Uptime | >99% |
| Knowledge coverage | >80% of common questions |

---

## Resource Requirements

### Development
- 1-2 developers
- ~300 hours total
- Test hardware (Pi 5 8GB)

### Initial Costs
- Domain registration: ~$15/year
- SSL certificate: Free (Let's Encrypt)
- Hosting (marketing site): ~$20/month
- Test hardware: ~$150

### Content
- FZJ80 FSM (legally obtained)
- Forum content (scraped with respect)
- Community contributions
