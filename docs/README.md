# AxleLore - Your Local Vehicle Intelligence Assistant

> **"Every wrench turn, every warning light, every mod - answered offline."**

## Vision

AxleLore is a local-first, privacy-focused LLM-powered vehicle assistant designed to run on affordable hardware like the Raspberry Pi. It provides instant access to vehicle-specific knowledge including factory service manuals, enthusiast forum wisdom, aftermarket modification guides, and your personal service history - all without requiring an internet connection.

## The Problem

1. **Information Fragmentation**: Vehicle knowledge is scattered across FSMs, forums (IH8MUD, Toyota-4Runner.org, etc.), YouTube, and word-of-mouth
2. **Internet Dependency**: Most solutions require constant connectivity
3. **Generic Advice**: ChatGPT and similar tools lack vehicle-specific depth and often hallucinate
4. **Lost Tribal Knowledge**: Forum posts get deleted, users leave, and decades of wisdom disappears
5. **No Personal Context**: Existing tools don't know YOUR vehicle's history or modifications

## The Solution

A pre-trained, vehicle-specific LLM assistant that:

- **Runs Locally**: Works in the garage, on the trail, anywhere - no internet needed
- **Knows Your Vehicle**: Pre-loaded with model-specific manuals, TSBs, common issues, and modifications
- **Preserves Forum Wisdom**: Curated knowledge from enthusiast communities distilled into searchable answers
- **Tracks Your Vehicle**: Service records, modifications, OBD2 data - all integrated
- **Grows With You**: Optional internet sync to update knowledge base and share (anonymized) data

## Target Market (MVP)

### Phase 1: Toyota Land Cruiser 80 Series (FZJ80)

Why this vehicle:
- Passionate, engaged community (IH8MUD is the gold standard)
- Complex vehicles with extensive modification potential
- Owners who wrench on their own vehicles
- Premium price tolerance (these owners spend $$$ on their trucks)
- Rich documentation history (Toyota FSMs are excellent)

### Future Expansion
- FJ80 (different engine - 3FE vs 1FZ-FE)
- 100 Series Land Cruiser
- Toyota 4Runner (3rd/4th/5th gen)
- Tacoma
- Lexus GX/LX
- Other Toyota trucks
- Eventually: Any vehicle with sufficient documentation

## Product Offerings

### 1. Software Download ($99-199)
- Download and self-install on your own hardware
- Includes installation guide
- Vehicle-specific knowledge pack

### 2. Pre-Loaded Hardware ($299-499)
- Raspberry Pi 5 (8GB) pre-configured
- SD card with OS and AxleLore
- OBD2 adapter included
- Ready to plug and play

### 3. Knowledge Pack Subscriptions ($29/year)
- Updated forum data
- New TSBs and recalls
- Community-contributed fixes
- Opt-in cloud backup of service records

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Hardware | Raspberry Pi 5 (8GB) | Affordable, available, sufficient for quantized models |
| LLM Runtime | Ollama | Easy deployment, quantized model support |
| Base Model | Mistral 7B (Q4_K_M) | Good performance at small size |
| Vector DB | ChromaDB | Lightweight, local, fast |
| Embeddings | all-MiniLM-L6-v2 | Fast, accurate, runs on Pi |
| Backend | FastAPI (Python) | Async, modern, good ecosystem |
| Frontend | Svelte/React (TBD) | Lightweight SPA |
| Database | SQLite | Zero-config, reliable |
| OBD2 | python-OBD | Well-maintained library |

## Key Features

### Core (MVP)
- [ ] Natural language Q&A about vehicle
- [ ] Service record tracking
- [ ] Parts lookup with part numbers
- [ ] Maintenance schedule tracking
- [ ] Common issues database

### Phase 2
- [ ] OBD2 live data display
- [ ] DTC code lookup and explanation
- [ ] Freeze frame analysis
- [ ] Service interval reminders

### Phase 3
- [ ] Voice interface
- [ ] Optional cloud sync
- [ ] Community knowledge sharing
- [ ] Modification tracking with impacts

## Name Considerations

**AxleLore** - Current favorite
- Combines "Axle" (automotive) with "Lore" (accumulated knowledge/wisdom)
- Memorable, available domain likely available
- Works well as brand

**Alternatives to consider:**
- WrenchWise
- GarageGPT
- ShopTalk AI
- MechanicMind
- TorqueTalk

## License

MIT License (open source core, commercial knowledge packs)

---

*Built by enthusiasts, for enthusiasts.*
