"""Smart document chunker for AxleLore."""
from dataclasses import dataclass
from typing import Optional
import re
import hashlib
import logging

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


class SmartChunker:
    """Intelligently chunk documents for RAG retrieval.
    
    Strategies:
    - Procedures: Keep steps together
    - Forum posts: Keep Q&A pairs together
    - Specifications: Group related specs
    - General text: Respect sentence boundaries
    """
    
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        min_chunk_size: int = 200
    ):
        """Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            min_chunk_size: Minimum chunk size to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_document(self, doc: dict) -> list[Chunk]:
        """Chunk a document based on its type.
        
        Args:
            doc: Document dict with 'source', 'content', etc.
            
        Returns:
            List of chunks
        """
        source = doc.get("source", "unknown")
        content = doc.get("content", "")
        
        if not content or len(content) < self.min_chunk_size:
            return []
        
        # Choose chunking strategy based on source
        if source == "fsm":
            return self._chunk_fsm(doc)
        elif source in ["ih8mud", "forum"]:
            return self._chunk_forum(doc)
        elif source == "parts":
            return self._chunk_parts(doc)
        else:
            return self._chunk_general(doc)
    
    def _chunk_fsm(self, doc: dict) -> list[Chunk]:
        """Chunk FSM content, keeping procedures together."""
        content = doc.get("content", "")
        title = doc.get("title", "")
        source_id = doc.get("source_id", "")
        category = doc.get("category", "general")
        
        chunks = []
        
        # Check if content has numbered steps
        has_steps = bool(re.search(r"^\s*\d+[\.\)]\s", content, re.MULTILINE))
        
        if has_steps:
            chunks = self._chunk_procedure(content, doc)
        else:
            chunks = self._chunk_by_sections(content, doc)
        
        # Add title context to each chunk
        for chunk in chunks:
            if title and title not in chunk.text:
                chunk.text = f"{title}\n\n{chunk.text}"
        
        return chunks
    
    def _chunk_procedure(self, content: str, doc: dict) -> list[Chunk]:
        """Chunk procedural content, keeping step groups together."""
        chunks = []
        
        # Split into steps
        step_pattern = r"(^\s*\d+[\.\)]\s.*?)(?=^\s*\d+[\.\)]\s|\Z)"
        steps = re.findall(step_pattern, content, re.MULTILINE | re.DOTALL)
        
        if not steps:
            return self._chunk_by_size(content, doc)
        
        current_chunk = ""
        step_start = 0
        
        for i, step in enumerate(steps):
            # Check if adding this step exceeds chunk size
            if len(current_chunk) + len(step) > self.chunk_size and current_chunk:
                chunk = self._create_chunk(
                    current_chunk,
                    doc,
                    suffix=f"_steps_{step_start}-{i}"
                )
                chunks.append(chunk)
                current_chunk = step
                step_start = i + 1
            else:
                current_chunk += step
        
        # Add final chunk
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunk = self._create_chunk(
                current_chunk,
                doc,
                suffix=f"_steps_{step_start}-{len(steps)}"
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_forum(self, doc: dict) -> list[Chunk]:
        """Chunk forum content, keeping Q&A together."""
        content = doc.get("content", "")
        title = doc.get("title", "")
        
        # For forum posts, include the question title in every chunk
        if title:
            content = f"Topic: {title}\n\n{content}"
        
        # If content is short enough, keep it together
        if len(content) <= self.chunk_size:
            return [self._create_chunk(content, doc)]
        
        # Split by response markers
        if "Response:" in content or "Answer:" in content:
            return self._chunk_qa(content, doc)
        
        return self._chunk_by_size(content, doc)
    
    def _chunk_qa(self, content: str, doc: dict) -> list[Chunk]:
        """Chunk Q&A content, keeping question with each answer."""
        chunks = []
        
        # Extract question part
        parts = re.split(r"\n(?=Response:|Answer:)", content)
        question = parts[0] if parts else ""
        responses = parts[1:] if len(parts) > 1 else []
        
        if not responses:
            return self._chunk_by_size(content, doc)
        
        for i, response in enumerate(responses):
            chunk_text = f"{question}\n\n{response}"
            
            # If still too long, truncate the response
            if len(chunk_text) > self.chunk_size:
                max_response = self.chunk_size - len(question) - 10
                response = response[:max_response] + "..."
                chunk_text = f"{question}\n\n{response}"
            
            chunk = self._create_chunk(chunk_text, doc, suffix=f"_qa_{i}")
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_parts(self, doc: dict) -> list[Chunk]:
        """Chunk parts catalog content."""
        content = doc.get("content", "")
        
        # Parts are usually already well-structured
        # Just ensure reasonable size
        return self._chunk_by_size(content, doc)
    
    def _chunk_general(self, doc: dict) -> list[Chunk]:
        """General chunking with sentence boundaries."""
        content = doc.get("content", "")
        return self._chunk_by_size(content, doc)
    
    def _chunk_by_sections(self, content: str, doc: dict) -> list[Chunk]:
        """Chunk by section headers."""
        chunks = []
        
        # Split by headers
        sections = re.split(r"\n(?=[A-Z][A-Z\s]+:|\#+ )", content)
        
        current_chunk = ""
        
        for section in sections:
            if len(current_chunk) + len(section) > self.chunk_size and current_chunk:
                chunk = self._create_chunk(current_chunk, doc)
                chunks.append(chunk)
                current_chunk = section
            else:
                current_chunk += "\n" + section if current_chunk else section
        
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(self._create_chunk(current_chunk, doc))
        
        return chunks if chunks else self._chunk_by_size(content, doc)
    
    def _chunk_by_size(self, content: str, doc: dict) -> list[Chunk]:
        """Simple size-based chunking with overlap."""
        chunks = []
        
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", content)
        
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(self._create_chunk(current_chunk, doc))
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                current_chunk = overlap_text + sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(self._create_chunk(current_chunk, doc))
        
        return chunks
    
    def _create_chunk(
        self,
        text: str,
        doc: dict,
        suffix: str = ""
    ) -> Chunk:
        """Create a Chunk object from text and document metadata."""
        source = doc.get("source", "unknown")
        source_id = doc.get("source_id", "")
        
        # Generate unique ID
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        chunk_id = f"{source}_{source_id}{suffix}_{text_hash}"
        
        # Build metadata, filtering out None values (ChromaDB rejects them)
        raw_meta = {
            "title": doc.get("title", ""),
            "url": doc.get("url", ""),
            "date": doc.get("date"),
            "quality_score": doc.get("quality_score", 0.0),
            "vehicle_type": doc.get("metadata", {}).get("vehicle_type", ""),
        }
        metadata = {
            k: v for k, v in raw_meta.items()
            if v is not None and not isinstance(v, (dict, list))
        }

        return Chunk(
            id=chunk_id,
            text=text.strip(),
            source=source,
            source_id=source_id,
            category=doc.get("category", "general"),
            metadata=metadata,
        )


def main():
    """Test chunker."""
    chunker = SmartChunker()
    
    # Test forum document
    forum_doc = {
        "source": "ih8mud",
        "source_id": "12345",
        "title": "Head gasket replacement tips?",
        "content": """Question: Head gasket replacement tips?
        
I'm about to tackle a head gasket replacement on my 1995 FZJ80. 
Any tips from those who have done it?

Response: Make sure you have the right torque specs. The 1FZ-FE 
head bolts need to be torqued to 29 ft-lbs first pass, then 90 degrees.
Use new head bolts, they're torque-to-yield.

Response: Also check the head for warpage before reinstalling. 
Maximum warpage spec is 0.05mm. Get it resurfaced if needed.""",
        "category": "engine"
    }
    
    chunks = chunker.chunk_document(forum_doc)
    
    for chunk in chunks:
        print(f"--- Chunk {chunk.id} ---")
        print(f"Category: {chunk.category}")
        print(f"Text: {chunk.text[:200]}...")
        print()


if __name__ == "__main__":
    main()
