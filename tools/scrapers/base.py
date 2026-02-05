"""Base scraper class for AxleLore data collection."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, AsyncIterator
import asyncio
import logging
import json

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ScrapedDocument:
    """A scraped document."""
    source: str  # 'ih8mud', 'fsm', etc.
    source_id: str  # Thread ID, page number, etc.
    url: str
    title: str
    content: str
    author: Optional[str] = None
    date: Optional[datetime] = None
    category: Optional[str] = None
    tags: list[str] = None
    quality_score: float = 0.0
    metadata: dict = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source,
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "date": self.date.isoformat() if self.date else None,
            "category": self.category,
            "tags": self.tags,
            "quality_score": self.quality_score,
            "metadata": self.metadata
        }


class BaseScraper(ABC):
    """Base class for all scrapers.
    
    Subclasses should implement:
    - scrape(): Main scraping logic
    - _extract_document(): Extract document from raw HTML
    """
    
    def __init__(
        self,
        output_dir: Path,
        rate_limit: float = 2.0,
        max_retries: int = 3,
        timeout: float = 30.0
    ):
        """Initialize scraper.
        
        Args:
            output_dir: Directory to save scraped data
            rate_limit: Minimum seconds between requests
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.timeout = timeout
        self._last_request = 0.0
        self.client: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "AxleLore/1.0 (Educational automotive knowledge collection)"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self._last_request = asyncio.get_event_loop().time()
    
    async def fetch(self, url: str) -> Optional[str]:
        """Fetch a URL with rate limiting and retries.
        
        Args:
            url: URL to fetch
            
        Returns:
            Response text or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                await self._rate_limit()
                response = await self.client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {url} - {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        return None
    
    @abstractmethod
    async def scrape(self) -> AsyncIterator[ScrapedDocument]:
        """Main scraping logic. Yields scraped documents."""
        pass
    
    def save_document(self, doc: ScrapedDocument):
        """Save a scraped document to disk."""
        filename = f"{doc.source}_{doc.source_id}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(doc.to_dict(), f, indent=2)
            
        logger.debug(f"Saved: {filepath}")
    
    def save_batch(self, docs: list[ScrapedDocument], batch_name: str):
        """Save a batch of documents."""
        filepath = self.output_dir / f"{batch_name}.jsonl"
        
        with open(filepath, "a") as f:
            for doc in docs:
                f.write(json.dumps(doc.to_dict()) + "\n")
                
        logger.info(f"Saved batch of {len(docs)} documents to {filepath}")
