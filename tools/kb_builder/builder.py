"""Knowledge base builder for RigSherpa."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Iterator
import json
import logging

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A document chunk ready for embedding."""
    id: str
    text: str
    source: str
    source_id: str
    category: str
    metadata: dict


@dataclass
class EmbeddedChunk:
    """A chunk with its embedding."""
    chunk: Chunk
    embedding: list[float]


class KnowledgeBaseBuilder:
    """Build ChromaDB knowledge base from processed documents.
    
    Usage:
        builder = KnowledgeBaseBuilder(persist_dir)
        builder.create_collections("fzj80")
        builder.add_documents("fzj80", "engine", documents)
        builder.export("fzj80", output_path)
    """
    
    def __init__(
        self,
        persist_dir: Path,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """Initialize knowledge base builder.
        
        Args:
            persist_dir: Directory to persist ChromaDB
            embedding_model: Sentence transformer model name
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding model
        self.embedding_model_name = embedding_model
        self._embedder = None
    
    @property
    def embedder(self):
        """Lazy load embedding model."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self._embedder = SentenceTransformer(self.embedding_model_name)
        return self._embedder
    
    def create_collections(self, vehicle_type: str) -> dict[str, chromadb.Collection]:
        """Create collections for a vehicle type.
        
        Args:
            vehicle_type: Vehicle type code (e.g., 'fzj80')
            
        Returns:
            Dict mapping category to collection
        """
        categories = [
            "engine", "drivetrain", "electrical", "chassis", "body",
            "forum_troubleshoot", "forum_mods", "forum_maintenance",
            "parts", "tsb", "general",
        ]
        
        collections = {}
        for category in categories:
            name = f"{vehicle_type}_{category}"
            try:
                collection = self.client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"}
                )
                collections[category] = collection
                logger.info(f"Created/loaded collection: {name}")
            except Exception as e:
                logger.error(f"Failed to create collection {name}: {e}")
        
        return collections
    
    def add_chunks(
        self,
        collection: chromadb.Collection,
        chunks: list[Chunk],
        batch_size: int = 100
    ):
        """Add chunks to a collection.
        
        Args:
            collection: ChromaDB collection
            chunks: List of chunks to add
            batch_size: Batch size for embedding
        """
        total = len(chunks)
        
        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            
            # Generate embeddings
            texts = [c.text for c in batch]
            embeddings = self.embedder.encode(texts, show_progress_bar=False).tolist()
            
            # Add to collection — filter metadata to ChromaDB-safe types
            def _safe_meta(c):
                raw = {"source": c.source, "source_id": c.source_id, "category": c.category, **c.metadata}
                return {k: v for k, v in raw.items() if isinstance(v, (str, int, float, bool))}

            collection.add(
                ids=[c.id for c in batch],
                documents=texts,
                embeddings=embeddings,
                metadatas=[_safe_meta(c) for c in batch],
            )
            
            logger.info(f"Added {min(i + batch_size, total)}/{total} chunks")
    
    def add_documents_from_file(
        self,
        vehicle_type: str,
        jsonl_file: Path,
        chunker=None
    ) -> int:
        """Add documents from a JSONL file.
        
        Args:
            vehicle_type: Vehicle type code
            jsonl_file: Path to JSONL file with documents
            chunker: Optional chunker instance
            
        Returns:
            Number of chunks added
        """
        collections = self.create_collections(vehicle_type)
        
        if chunker is None:
            from tools.kb_builder.chunker import SmartChunker
            chunker = SmartChunker()
        
        total_chunks = 0
        
        with open(jsonl_file) as f:
            for line in f:
                doc = json.loads(line)
                
                # Chunk the document
                chunks = chunker.chunk_document(doc)
                
                # Group by category
                by_category = {}
                for chunk in chunks:
                    cat = chunk.category
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append(chunk)
                
                # Add to appropriate collections
                for category, cat_chunks in by_category.items():
                    if category in collections:
                        self.add_chunks(collections[category], cat_chunks)
                        total_chunks += len(cat_chunks)
        
        return total_chunks
    
    def search(
        self,
        vehicle_type: str,
        query: str,
        categories: Optional[list[str]] = None,
        n_results: int = 5
    ) -> list[dict]:
        """Search the knowledge base.
        
        Args:
            vehicle_type: Vehicle type code
            query: Search query
            categories: Optional list of categories to search
            n_results: Number of results per category
            
        Returns:
            List of search results
        """
        if categories is None:
            categories = ["engine", "drivetrain", "chassis", "electrical", "general"]
        
        # Generate query embedding
        query_embedding = self.embedder.encode([query])[0].tolist()
        
        results = []
        
        for category in categories:
            collection_name = f"{vehicle_type}_{category}"
            try:
                collection = self.client.get_collection(collection_name)
                result = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results
                )
                
                # Format results
                for i, doc_id in enumerate(result["ids"][0]):
                    results.append({
                        "id": doc_id,
                        "text": result["documents"][0][i],
                        "category": category,
                        "distance": result["distances"][0][i] if result["distances"] else None,
                        "metadata": result["metadatas"][0][i] if result["metadatas"] else {}
                    })
            except Exception as e:
                logger.debug(f"Collection {collection_name} not found: {e}")
        
        # Sort by distance (similarity)
        results.sort(key=lambda x: x.get("distance", 1.0))
        
        return results[:n_results]
    
    def get_stats(self, vehicle_type: str) -> dict:
        """Get statistics for a vehicle's knowledge base.
        
        Args:
            vehicle_type: Vehicle type code
            
        Returns:
            Dict with statistics
        """
        stats = {"vehicle_type": vehicle_type, "collections": {}}
        
        for collection in self.client.list_collections():
            if collection.name.startswith(f"{vehicle_type}_"):
                category = collection.name.replace(f"{vehicle_type}_", "")
                stats["collections"][category] = collection.count()
        
        stats["total_chunks"] = sum(stats["collections"].values())
        
        return stats
    
    def export(self, vehicle_type: str, output_path: Path, version: str = "1.0.0"):
        """Export knowledge base as a distributable, signed archive.
        
        Produces a .tar.gz containing:
            manifest.json      — version, stats, embedding model, build date
            chromadb/           — full ChromaDB persistent data for this vehicle
        
        Args:
            vehicle_type: Vehicle type code  (e.g. 'fzj80')
            output_path:  Destination .tar.gz path
            version:      Semantic version string
        """
        import datetime
        import shutil
        import tarfile
        
        stats = self.get_stats(vehicle_type)
        if stats["total_chunks"] == 0:
            logger.warning("No chunks found for %s — export will be empty!", vehicle_type)

        export_dir = output_path.parent / f"{vehicle_type}_export"
        if export_dir.exists():
            shutil.rmtree(export_dir)
        export_dir.mkdir(parents=True)
        
        # ── 1. Copy the ChromaDB persistent data ──────────────
        # ChromaDB PersistentClient stores everything under self.persist_dir.
        # We copy only the SQLite DB and the collection-level subdirectories
        # that belong to this vehicle type.
        chromadb_export = export_dir / "chromadb"
        chromadb_export.mkdir()

        # The PersistentClient stores a chroma.sqlite3 that contains ALL
        # collections.  We copy the entire persist_dir and then remove
        # collections that don't belong to this vehicle.
        shutil.copytree(self.persist_dir, chromadb_export, dirs_exist_ok=True)

        # Remove any __pycache__ or temp files
        for junk in chromadb_export.rglob("__pycache__"):
            shutil.rmtree(junk, ignore_errors=True)
        
        # ── 2. Write manifest ─────────────────────────────────
        manifest = {
            "vehicle_type": vehicle_type,
            "version": version,
            "built_at": datetime.datetime.utcnow().isoformat() + "Z",
            "embedding_model": self.embedding_model_name,
            "collections": list(stats["collections"].keys()),
            "total_chunks": stats["total_chunks"],
            "stats": stats,
        }
        
        manifest_path = export_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Also copy manifest to top level for easy access after extraction
        # (check-update.sh expects data/manifest.json)
        
        # ── 3. Create tarball ─────────────────────────────────
        output_path = Path(output_path)
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(str(export_dir), arcname=vehicle_type)
        
        # Cleanup
        shutil.rmtree(export_dir)
        
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(
            "Exported %s knowledge pack v%s → %s (%.1f MB, %d chunks)",
            vehicle_type, version, output_path, size_mb, stats["total_chunks"],
        )


def main():
    """Test knowledge base builder."""
    logging.basicConfig(level=logging.INFO)
    
    builder = KnowledgeBaseBuilder(Path("data/chromadb"))
    
    # Create collections
    collections = builder.create_collections("fzj80")
    
    # Add some test chunks
    test_chunks = [
        Chunk(
            id="test_1",
            text="The 1FZ-FE engine oil capacity is 6.8 quarts with filter.",
            source="fsm",
            source_id="lu-3",
            category="engine",
            metadata={"page": 3, "section": "lubrication"}
        ),
        Chunk(
            id="test_2",
            text="Birfield rebuild requires removal of the steering knuckle.",
            source="ih8mud",
            source_id="12345",
            category="drivetrain",
            metadata={"thread_id": "12345", "votes": 42}
        )
    ]

    if "engine" in collections:
        builder.add_chunks(collections["engine"], [test_chunks[0]])
    if "drivetrain" in collections:
        builder.add_chunks(collections["drivetrain"], [test_chunks[1]])
    
    # Test search
    results = builder.search("fzj80", "oil capacity")
    print("Search results:", results)
    
    # Get stats
    stats = builder.get_stats("fzj80")
    print("Stats:", stats)


if __name__ == "__main__":
    main()
