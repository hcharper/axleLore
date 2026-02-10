"""RAG (Retrieval-Augmented Generation) service for AxleLore.

Manages ChromaDB vector search, embedding, context assembly, and source
citation formatting for the Qwen3 1.7B model on a Pi 5 (8 GB).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

import yaml
import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RetrievedChunk:
    text: str
    source: str
    source_id: str
    category: str
    score: float
    metadata: dict = field(default_factory=dict)


@dataclass
class RAGContext:
    chunks: list[RetrievedChunk]
    vehicle_context: Optional[str] = None
    formatted: str = ""


# ---------------------------------------------------------------------------
# Collection layout for a single vehicle type
# ---------------------------------------------------------------------------

COLLECTION_CATEGORIES: list[str] = [
    "engine",
    "drivetrain",
    "electrical",
    "chassis",
    "body",
    "forum_troubleshoot",
    "forum_mods",
    "forum_maintenance",
    "parts",
    "tsb",
    "general",
]

# Maps user-query keywords → collections to search (targeted retrieval).
# Loaded per-vehicle from config/vehicles/<type>_keywords.yaml.
# Falls back to a hardcoded default if no YAML is found.

_DEFAULT_KEYWORD_ROUTES: dict[str, list[str]] = {
    "engine": ["engine", "forum_troubleshoot", "tsb"],
    "oil": ["engine", "forum_maintenance"],
    "coolant": ["engine", "forum_troubleshoot"],
    "transmission": ["drivetrain", "forum_troubleshoot"],
    "axle": ["drivetrain", "forum_troubleshoot"],
    "brake": ["chassis", "forum_maintenance"],
    "suspension": ["chassis", "forum_mods"],
    "electrical": ["electrical", "forum_troubleshoot"],
    "wiring": ["electrical", "forum_troubleshoot"],
    "mod": ["forum_mods"],
    "install": ["forum_mods"],
    "part number": ["parts"],
    "replace": ["parts", "forum_maintenance"],
    "rust": ["body", "forum_troubleshoot"],
}

_DEFAULT_FALLBACK_COLLECTIONS: list[str] = [
    "engine", "drivetrain", "chassis", "forum_troubleshoot", "general",
]


def _load_keyword_routes(vehicle_type: str) -> tuple[dict[str, list[str]], list[str]]:
    """Load keyword → collection routing from a vehicle's YAML config.

    Returns (keyword_routes, default_collections).
    Falls back to built-in defaults if YAML is missing.
    """
    yaml_path = settings.vehicles_config_dir / f"{vehicle_type}_keywords.yaml"
    if yaml_path.is_file():
        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f) or {}
            routes = data.get("keyword_routes", {})
            defaults = data.get("default_collections", _DEFAULT_FALLBACK_COLLECTIONS)
            logger.info("Loaded keyword routing for %s (%d keywords)", vehicle_type, len(routes))
            return routes, defaults
        except Exception as exc:
            logger.warning("Failed to load %s: %s — using defaults", yaml_path, exc)
    return _DEFAULT_KEYWORD_ROUTES, _DEFAULT_FALLBACK_COLLECTIONS


class RAGService:
    """Retrieval-Augmented Generation service backed by ChromaDB."""

    def __init__(
        self,
        persist_dir: Path | None = None,
        embedding_model_name: str | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ) -> None:
        self.persist_dir = Path(persist_dir or settings.chromadb_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_model_name = embedding_model_name or settings.embedding_model
        self.top_k = top_k or settings.retrieval_top_k
        self.similarity_threshold = similarity_threshold or settings.similarity_threshold

        # Per-vehicle keyword routing (lazily loaded)
        self._keyword_routes: dict[str, dict[str, list[str]]] = {}
        self._default_collections: dict[str, list[str]] = {}

        # Lazy-loaded resources
        self._client: chromadb.ClientAPI | None = None
        self._embedder = None

    # -- lazy init --------------------------------------------------------

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info("ChromaDB client initialised at %s", self.persist_dir)
        return self._client

    @property
    def embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model: %s", self.embedding_model_name)
            self._embedder = SentenceTransformer(self.embedding_model_name)
        return self._embedder

    # -- public API -------------------------------------------------------

    def ensure_collections(self, vehicle_type: str) -> dict[str, chromadb.Collection]:
        """Create / load all collections for a vehicle type."""
        collections: dict[str, chromadb.Collection] = {}
        for cat in COLLECTION_CATEGORIES:
            name = f"{vehicle_type}_{cat}"
            collections[cat] = self.client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"}
            )
        return collections

    def retrieve(
        self,
        query: str,
        vehicle_type: str,
        categories: Sequence[str] | None = None,
        n_results: int | None = None,
    ) -> list[RetrievedChunk]:
        """Semantic search across relevant collections.

        If *categories* is ``None``, the query text is scanned for keywords to
        decide which collections to search.  Falls back to a broad default set.
        """
        n = n_results or self.top_k
        if categories is None:
            categories = self._route_query(query, vehicle_type=vehicle_type)

        query_embedding = self.embedder.encode([query])[0].tolist()

        all_results: list[RetrievedChunk] = []

        for cat in categories:
            col_name = f"{vehicle_type}_{cat}"
            try:
                collection = self.client.get_collection(col_name)
            except Exception:
                continue

            if collection.count() == 0:
                continue

            result = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n, collection.count()),
            )

            for i, doc_id in enumerate(result["ids"][0]):
                distance = result["distances"][0][i] if result["distances"] else 1.0
                score = 1.0 - distance  # cosine similarity
                if score < self.similarity_threshold:
                    continue
                all_results.append(
                    RetrievedChunk(
                        text=result["documents"][0][i],
                        source=result["metadatas"][0][i].get("source", cat)
                        if result["metadatas"]
                        else cat,
                        source_id=doc_id,
                        category=cat,
                        score=score,
                        metadata=result["metadatas"][0][i] if result["metadatas"] else {},
                    )
                )

        # Sort by relevance, deduplicate, truncate
        all_results.sort(key=lambda c: c.score, reverse=True)
        seen_texts: set[str] = set()
        unique: list[RetrievedChunk] = []
        for chunk in all_results:
            sig = chunk.text[:200]
            if sig not in seen_texts:
                seen_texts.add(sig)
                unique.append(chunk)
            if len(unique) >= n:
                break
        return unique

    def assemble_context(
        self,
        query: str,
        vehicle_type: str,
        vehicle_context: str | None = None,
        categories: Sequence[str] | None = None,
    ) -> RAGContext:
        """One-shot: retrieve chunks and format them for the LLM prompt."""
        chunks = self.retrieve(query, vehicle_type, categories=categories)
        ctx = RAGContext(chunks=chunks, vehicle_context=vehicle_context)
        ctx.formatted = self._format_for_prompt(ctx)
        return ctx

    def get_stats(self, vehicle_type: str) -> dict:
        """Return chunk counts per collection."""
        stats: dict[str, int] = {}
        total = 0
        for cat in COLLECTION_CATEGORIES:
            name = f"{vehicle_type}_{cat}"
            try:
                col = self.client.get_collection(name)
                count = col.count()
            except Exception:
                count = 0
            stats[cat] = count
            total += count
        return {"vehicle_type": vehicle_type, "collections": stats, "total_chunks": total}

    # -- internal helpers --------------------------------------------------

    def _route_query(self, query: str, vehicle_type: str | None = None) -> list[str]:
        """Keyword-based collection routing for targeted retrieval.

        Routes are loaded from config/vehicles/<type>_keywords.yaml on first
        use, then cached for the lifetime of the service.
        """
        vtype = vehicle_type or settings.default_vehicle

        # Lazy-load keyword routes for this vehicle type
        if vtype not in self._keyword_routes:
            routes, defaults = _load_keyword_routes(vtype)
            self._keyword_routes[vtype] = routes
            self._default_collections[vtype] = defaults

        routes = self._keyword_routes[vtype]
        defaults = self._default_collections[vtype]

        query_lower = query.lower()
        matched: set[str] = set()
        for keyword, cats in routes.items():
            if keyword in query_lower:
                matched.update(cats)
        if not matched:
            matched = set(defaults)
        return list(matched)

    @staticmethod
    def _format_for_prompt(ctx: RAGContext) -> str:
        parts: list[str] = []
        if ctx.vehicle_context:
            parts.append(f"=== YOUR VEHICLE ===\n{ctx.vehicle_context}")
        if ctx.chunks:
            parts.append("=== RETRIEVED KNOWLEDGE ===")
            for i, chunk in enumerate(ctx.chunks, 1):
                source_label = chunk.source.upper()
                title = chunk.metadata.get("title", "")
                header = f"[{i}] {source_label}"
                if title:
                    header += f" — {title}"
                parts.append(f"\n{header}\n{chunk.text}")
        return "\n\n".join(parts)
