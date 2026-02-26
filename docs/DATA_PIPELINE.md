# RigSherpa Data Pipeline

## Overview

The data pipeline transforms raw vehicle knowledge from multiple sources into a searchable, AI-ready knowledge base. This document covers the entire pipeline from data collection to deployment.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATA PIPELINE OVERVIEW                              │
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐ │
│  │   SOURCE    │    │  EXTRACT    │    │  PROCESS    │    │  BUILD   │ │
│  │   DATA      │───▶│  & CLEAN    │───▶│  & CHUNK    │───▶│  KB      │ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────────┘ │
│                                                                          │
│  • FSM PDFs         • OCR           • Normalize       • Embed           │
│  • Forum scraped    • Text extract  • Classify        • Index           │
│  • Parts catalogs   • Deduplicate   • Chunk           • Export          │
│  • TSBs             • Validate      • Tag             • Package         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Sources

### 1. Factory Service Manual (FSM)

**Source**: Toyota FZJ80 Factory Service Manual (1993-1997)

**Volumes**:
- Volume 1: Engine (1FZ-FE), Fuel System, Cooling
- Volume 2: Chassis, Suspension, Brakes, Steering
- Volume 3: Body, Electrical, HVAC
- Electrical Wiring Diagrams (EWD)

**Legal Considerations**:
- FSMs are typically copyrighted
- Options: Purchase legitimate copies, use specs only (not verbatim)
- Alternative: Use third-party repair guides (Haynes, Chilton)

**Extraction Process**:
```python
# tools/processors/fsm.py
class FSMProcessor:
    """Process Factory Service Manual PDFs."""
    
    def extract_pages(self, pdf_path: Path) -> List[Page]:
        """Extract text and images from PDF."""
        pass
    
    def classify_section(self, text: str) -> str:
        """Classify content into categories."""
        categories = [
            'engine', 'transmission', 'transfer_case',
            'axles', 'suspension', 'brakes', 'steering',
            'electrical', 'body', 'hvac', 'fuel'
        ]
        pass
    
    def extract_procedures(self, pages: List[Page]) -> List[Procedure]:
        """Extract step-by-step procedures."""
        pass
    
    def extract_specs(self, pages: List[Page]) -> List[Specification]:
        """Extract torque specs, capacities, etc."""
        pass
```

**Output Schema**:
```json
{
    "source": "fsm",
    "vehicle_type": "fzj80",
    "section": "engine",
    "subsection": "cylinder_head",
    "page": 123,
    "content_type": "procedure",
    "title": "Cylinder Head Bolt Torque Sequence",
    "content": "...",
    "specs": {
        "torque_ft_lbs": 58,
        "torque_nm": 78,
        "sequence": "spiral from center"
    },
    "related_parts": ["90911-02120"]
}
```

### 2. Forum Data (IH8MUD)

**Source**: https://forum.ih8mud.com/

**Target Sections**:
- 80-Series Tech
- Newbie Tech
- Parts & Vendors Reviews
- Build Threads

**Scraping Ethics**:
- Check robots.txt (currently allows with delays)
- Rate limit: 1 request per 2 seconds
- Cache aggressively
- Respect server load
- Attribute authors

**Scraper Implementation**:
```python
# tools/scrapers/ih8mud.py
class IH8MUDScraper(BaseScraper):
    """Scraper for IH8MUD forums."""
    
    BASE_URL = "https://forum.ih8mud.com"
    RATE_LIMIT = 2.0  # seconds between requests
    
    TARGET_FORUMS = [
        "forums/80-series-tech.9/",
        "forums/newbie-tech.162/",
    ]
    
    async def scrape_thread(self, url: str) -> Thread:
        """Scrape a single thread."""
        pass
    
    async def scrape_forum(self, forum_url: str, pages: int = 100) -> List[Thread]:
        """Scrape forum listing pages."""
        pass
    
    def extract_quality_posts(self, thread: Thread) -> List[Post]:
        """Filter to high-quality posts (votes, verified, length)."""
        pass
```

**Quality Filtering**:
- Minimum post length: 100 characters
- Prioritize posts with "likes" or "helpful"
- Include OP questions for context
- Flag "verified solution" posts
- Exclude off-topic, personal attacks

**Output Schema**:
```json
{
    "source": "ih8mud",
    "vehicle_type": "fzj80",
    "thread_id": "123456",
    "thread_title": "1FZ-FE Head Gasket Replacement Guide",
    "post_id": "789",
    "author": "username",
    "date": "2023-01-15",
    "content": "...",
    "category": "engine",
    "tags": ["head_gasket", "procedure", "diy"],
    "quality_score": 0.85,
    "votes": 42,
    "is_verified_solution": true
}
```

### 3. Parts Database

**Sources**:
- Toyota OEM parts catalogs (web scraping)
- Rock Auto (aftermarket reference)
- Common vendors (SOR, Cruiser Corps, etc.)

**Data Points**:
```json
{
    "part_number": "90911-02120",
    "oem_part_number": "90911-02120",
    "name": "Cylinder Head Bolt",
    "category": "engine",
    "subcategory": "cylinder_head",
    "vehicle_types": ["fzj80", "fj80"],
    "years": [1993, 1994, 1995, 1996, 1997],
    "quantity_needed": 14,
    "superseded_by": null,
    "price_range": {"low": 5.50, "high": 12.00},
    "common_vendors": ["Toyota Dealer", "Rock Auto", "SOR"],
    "notes": "Torque-to-yield, replace on every use"
}
```

### 4. Technical Service Bulletins (TSBs)

**Sources**:
- NHTSA database (public)
- Toyota TSB archives

**Data Points**:
```json
{
    "tsb_number": "EG-001-95",
    "date": "1995-03-15",
    "title": "1FZ-FE Oil Consumption Investigation",
    "vehicle_types": ["fzj80"],
    "years": [1993, 1994, 1995],
    "vins_affected": "JT3*...",
    "symptoms": ["excessive oil consumption", "blue smoke"],
    "cause": "Valve stem seal degradation",
    "remedy": "Replace valve stem seals",
    "parts": ["90913-02089"],
    "labor_time": 8.5
}
```

---

## Processing Pipeline

### Stage 1: Extraction

```python
# tools/processors/base.py
class BaseProcessor:
    """Base class for content processors."""
    
    def extract(self, source: Path) -> List[RawDocument]:
        """Extract raw content from source."""
        raise NotImplementedError
    
    def clean(self, doc: RawDocument) -> CleanedDocument:
        """Clean and normalize content."""
        # Remove HTML artifacts
        # Normalize whitespace
        # Fix encoding issues
        # Extract inline images
        pass
    
    def validate(self, doc: CleanedDocument) -> bool:
        """Validate document quality."""
        pass
```

### Stage 2: Classification

```python
# tools/processors/classifier.py
class ContentClassifier:
    """Classify content into categories and tags."""
    
    CATEGORIES = {
        'engine': ['1fz-fe', 'motor', 'head gasket', 'timing', 'oil'],
        'transmission': ['a442f', 'a440f', 'shift', 'gear', 'torque converter'],
        'transfer_case': ['transfer', '4wd', '2wd', 'hi', 'lo'],
        'axles': ['birfield', 'cv', 'knuckle', 'hub', 'diff', 'locker'],
        'suspension': ['spring', 'shock', 'lift', 'sway bar', 'bushing'],
        'brakes': ['pad', 'rotor', 'caliper', 'abs', 'brake line'],
        'steering': ['power steering', 'pump', 'rack', 'knuckle'],
        'electrical': ['wiring', 'ecu', 'sensor', 'relay', 'fuse'],
        'body': ['rust', 'paint', 'trim', 'door', 'window'],
        'cooling': ['radiator', 'thermostat', 'water pump', 'heater core'],
        'fuel': ['injector', 'fuel pump', 'tank', 'filter'],
        'exhaust': ['header', 'manifold', 'catalytic', 'muffler'],
        'modifications': ['lift', 'bumper', 'winch', 'rack', 'lights'],
    }
    
    def classify(self, text: str) -> Classification:
        """Classify text into category and tags."""
        pass
    
    def extract_entities(self, text: str) -> Entities:
        """Extract part numbers, specs, procedures."""
        pass
```

### Stage 3: Chunking

```python
# tools/kb_builder/chunker.py
class SmartChunker:
    """Intelligently chunk documents for RAG."""
    
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        min_chunk_size: int = 200
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Chunk document while preserving context."""
        # Strategy depends on document type:
        # - Procedures: Keep steps together
        # - Forum posts: Keep Q+A together
        # - Specs: Group related specs
        pass
    
    def chunk_procedure(self, procedure: Procedure) -> List[Chunk]:
        """Special chunking for procedures."""
        # Keep step numbers, don't break mid-step
        # Include title in each chunk
        pass
    
    def chunk_conversation(self, thread: Thread) -> List[Chunk]:
        """Chunk forum threads."""
        # Keep question with relevant answers
        # Include thread title for context
        pass
```

**Chunking Strategies**:

| Content Type | Strategy | Chunk Size |
|-------------|----------|------------|
| Procedures | Keep steps together | 600-1000 |
| Specifications | Group related | 400-600 |
| Forum Q&A | Question + answer | 800-1200 |
| Narratives | Sentence boundary | 800 |
| Parts lists | Natural groups | Variable |

### Stage 4: Embedding

```python
# tools/kb_builder/embedder.py
from sentence_transformers import SentenceTransformer

class Embedder:
    """Generate embeddings for chunks."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_chunks(self, chunks: List[Chunk]) -> List[EmbeddedChunk]:
        """Generate embeddings for all chunks."""
        texts = [chunk.text for chunk in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        return [
            EmbeddedChunk(chunk=c, embedding=e)
            for c, e in zip(chunks, embeddings)
        ]
    
    def batch_embed(
        self, 
        chunks: List[Chunk], 
        batch_size: int = 32
    ) -> Iterator[List[EmbeddedChunk]]:
        """Batch embedding for memory efficiency."""
        pass
```

### Stage 5: Indexing

```python
# tools/kb_builder/builder.py
import chromadb

class KnowledgeBaseBuilder:
    """Build ChromaDB knowledge base."""
    
    def __init__(self, persist_dir: Path):
        self.client = chromadb.PersistentClient(path=str(persist_dir))
    
    def create_collection(
        self, 
        vehicle_type: str, 
        category: str
    ) -> chromadb.Collection:
        """Create collection for vehicle/category."""
        name = f"{vehicle_type}_{category}"
        return self.client.create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_chunks(
        self, 
        collection: chromadb.Collection,
        chunks: List[EmbeddedChunk]
    ):
        """Add embedded chunks to collection."""
        collection.add(
            ids=[c.id for c in chunks],
            embeddings=[c.embedding for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks]
        )
    
    def build_vehicle_kb(
        self, 
        vehicle_type: str,
        sources: Dict[str, List[Document]]
    ) -> Path:
        """Build complete knowledge base for vehicle."""
        pass
```

---

## Knowledge Base Schema

### ChromaDB Collections

```
chromadb/
├── fzj80_engine/
│   └── metadata: source, page, procedure_id, category
├── fzj80_transmission/
├── fzj80_axles/
├── fzj80_electrical/
├── fzj80_forum/
│   └── metadata: thread_id, author, date, votes, is_solution
├── fzj80_parts/
│   └── metadata: part_number, category, years
└── fzj80_tsb/
    └── metadata: tsb_number, date, severity
```

### Metadata Schema

```python
class ChunkMetadata(BaseModel):
    """Standard metadata for all chunks."""
    
    # Source identification
    source: str  # 'fsm', 'ih8mud', 'parts', 'tsb'
    source_id: str  # page number, thread ID, etc.
    
    # Vehicle context
    vehicle_type: str  # 'fzj80'
    years: List[int]  # [1993, 1994, 1995, 1996, 1997]
    
    # Content classification
    category: str  # 'engine', 'axles', etc.
    subcategory: Optional[str]  # 'cylinder_head', etc.
    content_type: str  # 'procedure', 'spec', 'discussion', 'part'
    
    # Quality signals
    quality_score: float  # 0.0-1.0
    votes: Optional[int]  # forum votes
    is_verified: bool  # verified solution, official source
    
    # Temporal
    date: Optional[datetime]
    last_updated: datetime
    
    # Cross-references
    related_parts: List[str]  # part numbers
    related_procedures: List[str]  # procedure IDs
    related_chunks: List[str]  # linked chunk IDs
```

---

## Build Process

### Full Pipeline Execution

```bash
# 1. Run scrapers (can be done in parallel)
python -m tools.scrapers.ih8mud --output data/raw/forum/
python -m tools.scrapers.parts --output data/raw/parts/

# 2. Process FSM (manual step - requires PDFs)
python -m tools.processors.fsm --input /path/to/fsm/ --output data/raw/fsm/

# 3. Process all sources
python -m tools.processors.pipeline \
    --fsm data/raw/fsm/ \
    --forum data/raw/forum/ \
    --parts data/raw/parts/ \
    --output data/processed/

# 4. Build knowledge base
python -m tools.kb_builder.builder \
    --input data/processed/ \
    --output data/chromadb/ \
    --vehicle fzj80

# 5. Package for distribution
python -m tools.kb_builder.package \
    --input data/chromadb/ \
    --output dist/fzj80-knowledge-pack.tar.gz
```

### Incremental Updates

```python
# tools/kb_builder/updater.py
class KnowledgeBaseUpdater:
    """Update existing knowledge base with new content."""
    
    def identify_changes(
        self, 
        existing: ChromaDB, 
        new_data: List[Document]
    ) -> Changes:
        """Identify new, modified, and deleted documents."""
        pass
    
    def apply_updates(self, changes: Changes):
        """Apply incremental updates."""
        pass
    
    def full_rebuild_if_needed(self, threshold: float = 0.3):
        """Trigger full rebuild if too many changes."""
        pass
```

---

## Quality Assurance

### Validation Checks

```python
# tools/kb_builder/validator.py
class KnowledgeBaseValidator:
    """Validate knowledge base quality."""
    
    def check_coverage(self, kb: ChromaDB, vehicle_type: str) -> CoverageReport:
        """Check coverage across categories."""
        expected_categories = ['engine', 'transmission', ...]
        # Ensure minimum chunks per category
        pass
    
    def check_retrieval_quality(
        self, 
        kb: ChromaDB, 
        test_queries: List[Query]
    ) -> RetrievalReport:
        """Test retrieval with known queries."""
        pass
    
    def check_duplicates(self, kb: ChromaDB) -> DuplicateReport:
        """Find potential duplicates."""
        pass
```

### Test Queries (FZJ80)

```python
TEST_QUERIES = [
    {
        "query": "What's the oil capacity for a 1FZ-FE?",
        "expected_category": "engine",
        "expected_keywords": ["6.1", "6.8", "quarts", "5W-30"]
    },
    {
        "query": "How do I rebuild birfields?",
        "expected_category": "axles",
        "expected_keywords": ["knuckle", "grease", "seal"]
    },
    {
        "query": "Head gasket torque sequence",
        "expected_category": "engine",
        "expected_keywords": ["58", "ft-lb", "spiral", "center"]
    },
    # ... more test queries
]
```

---

## Distribution

### Knowledge Pack Format

```
fzj80-knowledge-pack-v1.0.0.tar.gz
├── manifest.json           # Version, checksums, counts
├── chromadb/               # ChromaDB export
│   ├── fzj80_engine/
│   ├── fzj80_transmission/
│   └── ...
├── metadata/               # Additional metadata
│   ├── categories.json
│   ├── parts_index.json
│   └── procedures_index.json
└── LICENSE.txt
```

### Manifest

```json
{
    "pack_name": "FZJ80 Knowledge Pack",
    "version": "1.0.0",
    "vehicle_type": "fzj80",
    "created_at": "2024-01-15T00:00:00Z",
    "stats": {
        "total_chunks": 12500,
        "sources": {
            "fsm": 5000,
            "forum": 6500,
            "parts": 800,
            "tsb": 200
        },
        "categories": {
            "engine": 2500,
            "axles": 1800,
            "electrical": 1500
        }
    },
    "checksums": {
        "chromadb": "sha256:...",
        "metadata": "sha256:..."
    },
    "compatibility": {
        "rigsherpa_version": ">=0.1.0",
        "chromadb_version": ">=0.4.0"
    }
}
```

---

## Expansion to Other Vehicles

### Vehicle Configuration

```yaml
# config/vehicles/fj80.yaml
vehicle_type: fj80
name: "Toyota Land Cruiser FJ80"
years: [1990, 1991, 1992]
engine: "3F-E"  # Different from FZJ80!

# Knowledge sharing with FZJ80
shared_knowledge:
  - axles        # Same axle design
  - suspension   # Same platform
  - body         # Same body
  - steering     # Same steering
  
# FJ80-specific
unique_systems:
  - engine       # 3F-E vs 1FZ-FE
  - fuel         # Carbureted vs EFI
  
# Adapt these from FZJ80
adapted_systems:
  - electrical   # Different ECU, many shared circuits
  - transmission # Similar A440F vs A442F
```

### Multi-Vehicle Pipeline

```python
# tools/kb_builder/multi_vehicle.py
class MultiVehicleBuilder:
    """Build knowledge bases for vehicle families."""
    
    def build_shared_kb(self, vehicle_family: str):
        """Build shared knowledge for vehicle family."""
        # e.g., "80_series" shared between FZJ80, FJ80
        pass
    
    def build_vehicle_specific(
        self, 
        vehicle_type: str,
        shared_kb: Path
    ):
        """Build vehicle-specific overlay."""
        pass
    
    def merge_for_distribution(
        self,
        vehicle_type: str,
        shared_kb: Path,
        specific_kb: Path
    ) -> Path:
        """Create distributable package with merged KB."""
        pass
```
