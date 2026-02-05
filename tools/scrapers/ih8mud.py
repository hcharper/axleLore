"""IH8MUD forum scraper for AxleLore."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional
import re
import logging

from bs4 import BeautifulSoup

from tools.scrapers.base import BaseScraper, ScrapedDocument

logger = logging.getLogger(__name__)


@dataclass
class ForumPost:
    """A single forum post."""
    post_id: str
    author: str
    date: datetime
    content: str
    likes: int = 0
    is_solution: bool = False


@dataclass 
class ForumThread:
    """A forum thread with posts."""
    thread_id: str
    title: str
    url: str
    forum_section: str
    posts: list[ForumPost]
    views: int = 0
    replies: int = 0


class IH8MUDScraper(BaseScraper):
    """Scraper for IH8MUD Toyota forums.
    
    Targets:
    - 80-Series Tech forum
    - Newbie Tech forum
    - Build threads
    
    Respects robots.txt and rate limits.
    """
    
    BASE_URL = "https://forum.ih8mud.com"
    
    # Target forum sections for FZJ80 content
    TARGET_FORUMS = {
        "80_series_tech": "forums/80-series-tech.9/",
        "newbie_tech": "forums/newbie-tech.162/",
    }
    
    # Quality filters
    MIN_POST_LENGTH = 100
    MIN_LIKES_FOR_PRIORITY = 5
    
    def __init__(
        self,
        output_dir: Path,
        vehicle_type: str = "fzj80",
        max_pages: int = 100,
        **kwargs
    ):
        super().__init__(output_dir, rate_limit=2.0, **kwargs)
        self.vehicle_type = vehicle_type
        self.max_pages = max_pages
    
    async def scrape(self) -> AsyncIterator[ScrapedDocument]:
        """Scrape IH8MUD forums."""
        for forum_name, forum_path in self.TARGET_FORUMS.items():
            logger.info(f"Scraping forum: {forum_name}")
            
            async for doc in self._scrape_forum(forum_name, forum_path):
                yield doc
    
    async def _scrape_forum(
        self, 
        forum_name: str, 
        forum_path: str
    ) -> AsyncIterator[ScrapedDocument]:
        """Scrape a single forum section."""
        page = 1
        
        while page <= self.max_pages:
            url = f"{self.BASE_URL}/{forum_path}page-{page}"
            html = await self.fetch(url)
            
            if not html:
                break
                
            thread_urls = self._extract_thread_urls(html)
            
            if not thread_urls:
                logger.info(f"No more threads in {forum_name} at page {page}")
                break
            
            for thread_url in thread_urls:
                try:
                    thread = await self._scrape_thread(thread_url)
                    if thread:
                        docs = self._thread_to_documents(thread, forum_name)
                        for doc in docs:
                            yield doc
                except Exception as e:
                    logger.error(f"Error scraping thread {thread_url}: {e}")
            
            page += 1
    
    def _extract_thread_urls(self, html: str) -> list[str]:
        """Extract thread URLs from forum listing page."""
        soup = BeautifulSoup(html, "lxml")
        urls = []
        
        # IH8MUD uses XenForo, thread links have specific structure
        for link in soup.select(".structItem-title a"):
            href = link.get("href", "")
            if href and "/threads/" in href:
                full_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href
                urls.append(full_url)
        
        return urls
    
    async def _scrape_thread(self, url: str) -> Optional[ForumThread]:
        """Scrape a single thread."""
        html = await self.fetch(url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, "lxml")
        
        # Extract thread metadata
        title_elem = soup.select_one(".p-title-value")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown"
        
        # Extract thread ID from URL
        thread_id_match = re.search(r"/threads/[^/]+\.(\d+)", url)
        thread_id = thread_id_match.group(1) if thread_id_match else url
        
        # Extract posts
        posts = []
        for post_elem in soup.select("article.message"):
            post = self._extract_post(post_elem)
            if post:
                posts.append(post)
        
        if not posts:
            return None
            
        return ForumThread(
            thread_id=thread_id,
            title=title,
            url=url,
            forum_section="",  # Will be set by caller
            posts=posts
        )
    
    def _extract_post(self, post_elem) -> Optional[ForumPost]:
        """Extract a single post from HTML element."""
        try:
            # Post ID
            post_id = post_elem.get("data-content", "").replace("post-", "")
            
            # Author
            author_elem = post_elem.select_one(".message-name")
            author = author_elem.get_text(strip=True) if author_elem else "Unknown"
            
            # Date
            date_elem = post_elem.select_one("time")
            date_str = date_elem.get("datetime", "") if date_elem else ""
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else None
            
            # Content
            content_elem = post_elem.select_one(".message-body .bbWrapper")
            content = content_elem.get_text(strip=True) if content_elem else ""
            
            # Clean up content
            content = self._clean_content(content)
            
            if len(content) < self.MIN_POST_LENGTH:
                return None
            
            # Likes
            likes_elem = post_elem.select_one(".reactionsBar-link")
            likes = 0
            if likes_elem:
                likes_text = likes_elem.get_text(strip=True)
                likes_match = re.search(r"(\d+)", likes_text)
                likes = int(likes_match.group(1)) if likes_match else 0
            
            return ForumPost(
                post_id=post_id,
                author=author,
                date=date,
                content=content,
                likes=likes
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract post: {e}")
            return None
    
    def _clean_content(self, content: str) -> str:
        """Clean post content."""
        # Remove excessive whitespace
        content = re.sub(r"\s+", " ", content)
        # Remove quote blocks (they're duplicate content)
        content = re.sub(r"Click to expand\.\.\.", "", content)
        return content.strip()
    
    def _thread_to_documents(
        self, 
        thread: ForumThread, 
        forum_section: str
    ) -> list[ScrapedDocument]:
        """Convert thread to ScrapedDocument objects."""
        documents = []
        
        # Create a document for the thread as a whole (Q&A style)
        if thread.posts:
            # First post is usually the question
            question = thread.posts[0]
            
            # Find best answer (most likes, or marked solution)
            answers = thread.posts[1:]
            best_answers = sorted(answers, key=lambda p: p.likes, reverse=True)[:5]
            
            # Combine into single document
            content_parts = [
                f"Question: {thread.title}",
                f"",
                question.content,
                "",
                "Responses:",
            ]
            
            for answer in best_answers:
                if answer.content:
                    content_parts.append(f"- {answer.content[:500]}")
            
            combined_content = "\n".join(content_parts)
            
            # Calculate quality score
            total_likes = sum(p.likes for p in thread.posts)
            quality_score = min(1.0, total_likes / 50)  # Normalize
            
            # Classify category based on content
            category = self._classify_content(combined_content)
            
            doc = ScrapedDocument(
                source="ih8mud",
                source_id=thread.thread_id,
                url=thread.url,
                title=thread.title,
                content=combined_content,
                author=question.author,
                date=question.date,
                category=category,
                tags=self._extract_tags(thread.title + " " + combined_content),
                quality_score=quality_score,
                metadata={
                    "forum_section": forum_section,
                    "total_posts": len(thread.posts),
                    "total_likes": total_likes,
                    "vehicle_type": self.vehicle_type
                }
            )
            documents.append(doc)
        
        return documents
    
    def _classify_content(self, text: str) -> str:
        """Classify content into category."""
        text_lower = text.lower()
        
        categories = {
            "engine": ["1fz", "engine", "head gasket", "timing", "oil", "coolant", "overheating"],
            "transmission": ["transmission", "a442f", "shift", "torque converter", "atf"],
            "axles": ["birfield", "cv joint", "knuckle", "hub", "diff", "locker", "axle"],
            "suspension": ["lift", "spring", "shock", "sway bar", "suspension"],
            "brakes": ["brake", "rotor", "pad", "caliper", "abs"],
            "electrical": ["wiring", "ecu", "sensor", "relay", "fuse", "electrical"],
            "steering": ["steering", "power steering", "rack"],
            "body": ["rust", "paint", "body", "door", "window"],
            "modifications": ["lift kit", "bumper", "winch", "rack", "lights", "mod"],
        }
        
        for category, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                return category
                
        return "general"
    
    def _extract_tags(self, text: str) -> list[str]:
        """Extract relevant tags from text."""
        tags = []
        text_lower = text.lower()
        
        tag_patterns = [
            ("1fz-fe", ["1fz", "1fz-fe"]),
            ("fzj80", ["fzj80", "80 series"]),
            ("diy", ["how to", "step by step", "procedure"]),
            ("troubleshooting", ["problem", "issue", "help", "won't"]),
            ("parts", ["part number", "oem", "replace"]),
        ]
        
        for tag, patterns in tag_patterns:
            if any(p in text_lower for p in patterns):
                tags.append(tag)
                
        return tags


async def main():
    """Run the IH8MUD scraper."""
    import asyncio
    from pathlib import Path
    
    logging.basicConfig(level=logging.INFO)
    
    output_dir = Path("data/raw/forum")
    
    async with IH8MUDScraper(output_dir, max_pages=5) as scraper:
        count = 0
        async for doc in scraper.scrape():
            scraper.save_document(doc)
            count += 1
            
            if count % 10 == 0:
                logger.info(f"Scraped {count} documents")
        
        logger.info(f"Scraping complete. Total documents: {count}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
