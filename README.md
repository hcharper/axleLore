# RigSherpa

> Local LLM-powered vehicle assistant for Raspberry Pi

**Your offline, AI-powered vehicle manual that knows your specific truck.**

## Quick Start

### Prerequisites

- Raspberry Pi 5 (8GB) or compatible Linux machine
- Python 3.11+
- 64GB+ storage

### Installation

```bash
# Clone repository
git clone https://github.com/harperWebServicesLLC/rigSherpa.git
cd rigSherpa

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Install Ollama (if not installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the model
ollama pull qwen3:1.7b

# Start the server
python -m backend.main
```

### Access

Open http://localhost:8000 in your browser.

## Features

- **Offline Q&A**: Ask questions about your vehicle without internet
- **Service Tracking**: Log maintenance and repairs
- **Parts Lookup**: Find part numbers instantly
- **Vehicle Context**: AI knows your specific truck's history
- **OBD2 Integration**: Connect to read codes and live data (Phase 2)

## Supported Vehicles (MVP)

- Toyota Land Cruiser FZJ80 (1993-1997)

## Documentation

- [Project Overview](docs/README.md)
- [Architecture](docs/ARCHITECTURE.md)
- [MVP Roadmap](docs/MVP_ROADMAP.md)
- [Data Pipeline](docs/DATA_PIPELINE.md)
- [Vehicle Schema](docs/VEHICLE_SCHEMA.md)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tools/
ruff check src/ tools/

# Type check
mypy src/
```

## License

MIT License - See [LICENSE](LICENSE) for details.

---

*Built by enthusiasts, for enthusiasts.*
