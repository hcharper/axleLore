"""RAG (Retrieval Augmented Generation) service for AxleLore."""
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved document chunk."""
    text: str
    source: str
    source_id: str
    category: str
    score: float
    metadata: dict


@dataclass
class RAGContext:
    """Context assembled for LLM prompt."""
    chunks: list[RetrievedChunk]
    vehicle_context: Optional[str]
    total_tokens: int


class RAGService:
    """Retrieval Augmented Generation service.
    
    Handles:
    - Query embedding
    - Vector store retrieval
    - Context assembly
    - Prompt construction
    """
    
    def __init__(
        self,
        chroma_client,
        embedding_model,
        chunk_size: int = 800,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ):
        self.chroma = chroma_client
        self.embedder = embedding_model
        self.chunk_size = chunk_size
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
    
    async def retrieve(
        self,
        query: str,
        vehicle_type: str,
        categories: Optional[list[str]] = None
    ) -> list[RetrievedChunk]:
        """Retrieve relevant chunks for a query.
        
        Args:
            query: User's question
            vehicle_type: Vehicle type code (e.g., 'fzj80')
            categories: Optional category filter
            
        Returns:
            List of relevant document chunks
        """
        # TODO: Implement vector search
        # 1. Generate embedding for query
        # 2. Search ChromaDB collections
        # 3. Filter by similarity threshold
        # 4. Return top-k results
        
        logger.info(f"Retrieving chunks for: {query[:50]}...")
        return []
    
    async def assemble_context(
        self,
        chunks: list[RetrievedChunk],
        vehicle_context: Optional[str] = None,
        max_tokens: int = 3000
    ) -> RAGContext:
        """Assemble context for LLM prompt.
        
        Args:
            chunks: Retrieved document chunks
            vehicle_context: Optional vehicle-specific context
            max_tokens: Maximum tokens for context
            
        Returns:
            Assembled RAG context
        """
        # TODO: Implement context assembly
        # 1. Deduplicate chunks
        # 2. Rerank if needed
        # 3. Trim to max_tokens
        # 4. Format with source citations
        
        return RAGContext(
            chunks=chunks,
            vehicle_context=vehicle_context,
            total_tokens=0
        )
    
    def format_context_for_prompt(self, context: RAGContext) -> str:
        """Format RAG context for inclusion in prompt."""
        parts = []
        
        if context.vehicle_context:
            parts.append(f"=== Your Vehicle ===\n{context.vehicle_context}")
        
        if context.chunks:
            parts.append("=== Relevant Information ===")
            for i, chunk in enumerate(context.chunks, 1):
                parts.append(f"\n[{i}] Source: {chunk.source}\n{chunk.text}")
        
        return "\n\n".join(parts)
