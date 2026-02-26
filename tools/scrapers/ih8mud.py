"""IH8MUD forum scraper for AxleLore.

Two-pass architecture:
  Pass 1 (index):  Crawl listing pages, extract thread URLs + metadata
  Pass 2 (content): Fetch full thread content (multi-page) for unscraped threads

Usage:
    python -m tools.scrapers.ih8mud                           # full run (index + content)
    python -m tools.scrapers.ih8mud --index-only              # build thread index only
    python -m tools.scrapers.ih8mud --max-threads 500         # limit content scraping
    python -m tools.scrapers.ih8mud --forum 80_series_tech    # single forum only
    python -m tools.scrapers.ih8mud --no-resume               # ignore saved state
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional

from bs4 import BeautifulSoup

from tools.scrapers.base import BaseScraper, ScrapedDocument
from tools.scrapers.state import ScrapeStateManager

logger = logging.getLogger(__name__)


@dataclass
class ForumPost:
    """A single forum post."""
    post_id: str
    author: str
    date: Optional[datetime]
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


@dataclass
class ThreadIndexEntry:
    """Thread metadata from a listing page."""
    thread_id: str
    title: str
    url: str
    replies: int
    views: int
    last_activity: str


class IH8MUDScraper(BaseScraper):
    """Scraper for IH8MUD Toyota forums.

    Targets 80-series tech, FZJ80 subforum, and newbie tech.
    Two-pass: index listing pages, then scrape individual threads.
    Supports resume via ScrapeStateManager.
    """

    BASE_URL = "https://forum.ih8mud.com"

    TARGET_FORUMS = {
        "80_series_tech": "forums/80-series-tech.9/",
        "fzj80_subforum": "forums/fj80-fzj80-lx450-hdj81.325/",
        "newbie_tech": "forums/newbie-tech.162/",
    }

    MIN_POST_LENGTH = 100
    MAX_THREAD_PAGES = 10

    def __init__(
        self,
        output_dir: Path = Path("data/raw/forum"),
        vehicle_type: str = "fzj80",
        max_pages: int = 5000,
        max_threads: int | None = None,
        target_forum: str | None = None,
        resume: bool = True,
        index_only: bool = False,
        **kwargs,
    ):
        super().__init__(output_dir, rate_limit=2.0, **kwargs)
        self.vehicle_type = vehicle_type
        self.max_pages = max_pages
        self.max_threads = max_threads
        self.target_forum = target_forum
        self.resume = resume
        self.index_only = index_only
        self._state: Optional[ScrapeStateManager] = None

    @property
    def state(self) -> ScrapeStateManager:
        if self._state is None:
            self._state = ScrapeStateManager(self.output_dir / ".." / "scrape_state.db")
        return self._state

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def scrape(self) -> AsyncIterator[ScrapedDocument]:
        """Run the two-pass scrape."""
        # Pass 1: Build thread index
        await self._pass_index()

        if self.index_only:
            logger.info("Index-only mode — skipping content scraping")
            return

        # Pass 2: Scrape thread content
        async for doc in self._pass_content():
            yield doc

    # ------------------------------------------------------------------
    # Pass 1: Index
    # ------------------------------------------------------------------

    async def _pass_index(self) -> None:
        """Crawl listing pages and build the thread index."""
        forums = self.TARGET_FORUMS
        if self.target_forum:
            if self.target_forum not in forums:
                logger.error("Unknown forum: %s  (choices: %s)",
                             self.target_forum, ", ".join(forums))
                return
            forums = {self.target_forum: forums[self.target_forum]}

        index_path = self.output_dir / "thread_index.jsonl"
        index_path.parent.mkdir(parents=True, exist_ok=True)

        for forum_name, forum_path in forums.items():
            state_key = f"ih8mud_index_{forum_name}"
            start_page = self.state.get_resume_page(state_key) if self.resume else 1
            if start_page < 1:
                start_page = 1

            logger.info("Indexing %s from page %d ...", forum_name, start_page)
            self.state.set_status(state_key, "running")

            page = start_page
            while page <= self.max_pages:
                url = f"{self.BASE_URL}/{forum_path}page-{page}"
                html = await self.fetch(url)
                if not html:
                    break

                entries = self._extract_thread_index(html, forum_name)
                if not entries:
                    logger.info("No more threads in %s at page %d", forum_name, page)
                    break

                # Append to index file
                with open(index_path, "a") as f:
                    for entry in entries:
                        f.write(json.dumps({
                            "thread_id": entry.thread_id,
                            "title": entry.title,
                            "url": entry.url,
                            "replies": entry.replies,
                            "views": entry.views,
                            "last_activity": entry.last_activity,
                            "forum": forum_name,
                        }) + "\n")

                self.state.mark_page_done(state_key, page)

                if page % 50 == 0:
                    logger.info("  %s: indexed page %d", forum_name, page)

                page += 1

            self.state.set_status(state_key, "done")
            logger.info("Finished indexing %s (pages %d-%d)", forum_name, start_page, page - 1)

    def _extract_thread_index(self, html: str, forum_name: str) -> list[ThreadIndexEntry]:
        """Extract thread metadata from a listing page."""
        soup = BeautifulSoup(html, "lxml")
        entries: list[ThreadIndexEntry] = []

        for item in soup.select(".structItem"):
            title_link = item.select_one(".structItem-title a")
            if not title_link:
                continue

            href = title_link.get("href", "")
            if "/threads/" not in href:
                continue

            title = title_link.get_text(strip=True)
            full_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href

            # Extract thread ID
            tid_match = re.search(r"\.(\d+)/?$", href)
            thread_id = tid_match.group(1) if tid_match else ""

            # Replies / views
            replies = 0
            views = 0
            pairs = item.select(".pairs--justified dd")
            if len(pairs) >= 1:
                replies = self._parse_count(pairs[0].get_text(strip=True))
            if len(pairs) >= 2:
                views = self._parse_count(pairs[1].get_text(strip=True))

            # Last activity
            time_tag = item.select_one("time")
            last_activity = time_tag.get("datetime", "") if time_tag else ""

            entries.append(ThreadIndexEntry(
                thread_id=thread_id,
                title=title,
                url=full_url,
                replies=replies,
                views=views,
                last_activity=last_activity,
            ))

        return entries

    @staticmethod
    def _parse_count(text: str) -> int:
        """Parse '1.2K' style counts to int."""
        text = text.strip().upper().replace(",", "")
        if text.endswith("K"):
            return int(float(text[:-1]) * 1000)
        if text.endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        try:
            return int(text)
        except ValueError:
            return 0

    # ------------------------------------------------------------------
    # Pass 2: Content
    # ------------------------------------------------------------------

    async def _pass_content(self) -> AsyncIterator[ScrapedDocument]:
        """Scrape thread content for unscraped threads in the index."""
        index_path = self.output_dir / "thread_index.jsonl"
        if not index_path.exists():
            logger.warning("No thread index found at %s — run index pass first", index_path)
            return

        # Load index
        threads: list[dict] = []
        with open(index_path) as f:
            for line in f:
                threads.append(json.loads(line))

        logger.info("Thread index has %d entries", len(threads))

        # Deduplicate by thread_id
        seen: set[str] = set()
        unique: list[dict] = []
        for t in threads:
            tid = t["thread_id"]
            if tid and tid not in seen:
                seen.add(tid)
                unique.append(t)
        threads = unique

        # Sort by engagement (replies * 0.3 + views * 0.01) descending — best content first
        threads.sort(key=lambda t: t.get("replies", 0) * 0.3 + t.get("views", 0) * 0.01, reverse=True)

        scraped = 0
        for entry in threads:
            if self.max_threads and scraped >= self.max_threads:
                break

            tid = entry["thread_id"]
            if self.state.is_item_done("ih8mud_content", tid):
                continue

            try:
                thread = await self._scrape_thread(entry["url"])
                if thread:
                    thread.forum_section = entry.get("forum", "")
                    thread.views = entry.get("views", 0)
                    thread.replies = entry.get("replies", 0)

                    # Save raw thread data
                    threads_dir = self.output_dir / "threads"
                    threads_dir.mkdir(parents=True, exist_ok=True)
                    raw = {
                        "thread_id": thread.thread_id,
                        "title": thread.title,
                        "url": thread.url,
                        "forum_section": thread.forum_section,
                        "views": thread.views,
                        "replies": thread.replies,
                        "posts": [
                            {
                                "post_id": p.post_id,
                                "author": p.author,
                                "date": p.date.isoformat() if p.date else None,
                                "content": p.content,
                                "likes": p.likes,
                                "is_solution": p.is_solution,
                            }
                            for p in thread.posts
                        ],
                    }
                    with open(threads_dir / f"{tid}.json", "w") as f:
                        json.dump(raw, f, indent=2)

                    # Convert to ScrapedDocuments
                    docs = self._thread_to_documents(thread, thread.forum_section)
                    for doc in docs:
                        yield doc

                    self.state.mark_item_done("ih8mud_content", tid)
                    scraped += 1

                    if scraped % 50 == 0:
                        logger.info("Scraped %d threads", scraped)

            except Exception as e:
                logger.error("Error scraping thread %s: %s", tid, e)

        logger.info("Content pass complete: scraped %d threads", scraped)

    async def _scrape_thread(self, url: str) -> Optional[ForumThread]:
        """Scrape a thread across multiple pages."""
        all_posts: list[ForumPost] = []
        title = "Unknown"
        thread_id = ""

        for page_num in range(1, self.MAX_THREAD_PAGES + 1):
            page_url = url if page_num == 1 else f"{url}page-{page_num}"
            html = await self.fetch(page_url)
            if not html:
                break

            soup = BeautifulSoup(html, "lxml")

            # Extract metadata from first page
            if page_num == 1:
                title_elem = soup.select_one(".p-title-value")
                title = title_elem.get_text(strip=True) if title_elem else "Unknown"
                tid_match = re.search(r"/threads/[^/]+\.(\d+)", url)
                thread_id = tid_match.group(1) if tid_match else url

            # Extract posts from this page
            for post_elem in soup.select("article.message"):
                post = self._extract_post(post_elem)
                if post:
                    all_posts.append(post)

            # Check for next page
            if not soup.select_one(".pageNav-page--later"):
                break

        if not all_posts:
            return None

        return ForumThread(
            thread_id=thread_id,
            title=title,
            url=url,
            forum_section="",
            posts=all_posts,
        )

    def _extract_post(self, post_elem) -> Optional[ForumPost]:
        """Extract a single post from HTML element."""
        try:
            post_id = post_elem.get("data-content", "").replace("post-", "")

            author_elem = post_elem.select_one(".message-name")
            author = author_elem.get_text(strip=True) if author_elem else "Unknown"

            date_elem = post_elem.select_one("time")
            date_str = date_elem.get("datetime", "") if date_elem else ""
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else None

            content_elem = post_elem.select_one(".message-body .bbWrapper")
            content = content_elem.get_text(strip=True) if content_elem else ""
            content = self._clean_content(content)

            if len(content) < self.MIN_POST_LENGTH:
                return None

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
                likes=likes,
            )

        except Exception as e:
            logger.debug("Failed to extract post: %s", e)
            return None

    def _clean_content(self, content: str) -> str:
        """Clean post content."""
        content = re.sub(r"\s+", " ", content)
        content = re.sub(r"Click to expand\.\.\.", "", content)
        return content.strip()

    def _thread_to_documents(
        self,
        thread: ForumThread,
        forum_section: str,
    ) -> list[ScrapedDocument]:
        """Convert thread to ScrapedDocument objects."""
        documents = []

        if not thread.posts:
            return documents

        question = thread.posts[0]
        answers = thread.posts[1:]
        best_answers = sorted(answers, key=lambda p: p.likes, reverse=True)[:5]

        content_parts = [
            f"Question: {thread.title}",
            "",
            question.content,
            "",
            "Responses:",
        ]

        for answer in best_answers:
            if answer.content:
                content_parts.append(f"- {answer.content[:500]}")

        combined_content = "\n".join(content_parts)

        total_likes = sum(p.likes for p in thread.posts)
        quality_score = min(1.0, total_likes / 50)

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
                "views": thread.views,
                "replies": thread.replies,
                "vehicle_type": self.vehicle_type,
            },
        )
        documents.append(doc)

        return documents

    def _classify_content(self, text: str) -> str:
        """Classify content into a ChromaDB category."""
        text_lower = text.lower()

        categories = {
            "engine": ["1fz", "engine", "head gasket", "timing", "oil", "coolant", "overheating"],
            "drivetrain": ["birfield", "cv joint", "knuckle", "hub", "diff", "locker", "axle",
                           "transmission", "a442f", "shift", "torque converter", "transfer case"],
            "electrical": ["wiring", "ecu", "sensor", "relay", "fuse", "electrical", "alternator"],
            "chassis": ["brake", "rotor", "pad", "caliper", "abs",
                        "lift", "spring", "shock", "sway bar", "suspension",
                        "steering", "power steering", "rack"],
            "body": ["rust", "paint", "body", "door", "window"],
            "forum_mods": ["lift kit", "bumper", "winch", "rack", "lights", "mod", "build",
                           "install", "upgrade", "swap"],
            "forum_maintenance": ["oil change", "maintenance", "service", "filter", "flush"],
        }

        for category, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                return category

        return "forum_troubleshoot"

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


async def run_scraper(
    max_threads: int | None = None,
    target_forum: str | None = None,
    index_only: bool = False,
    resume: bool = True,
) -> Path:
    """Run the IH8MUD scraper and return output directory."""
    output_dir = Path("data/raw/forum")
    async with IH8MUDScraper(
        output_dir,
        max_threads=max_threads,
        target_forum=target_forum,
        index_only=index_only,
        resume=resume,
    ) as scraper:
        count = 0
        async for doc in scraper.scrape():
            scraper.save_document(doc)
            count += 1
            if count % 10 == 0:
                logger.info("Scraped %d documents", count)
        logger.info("Scraping complete. Total documents: %d", count)
    return output_dir


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Scrape IH8MUD forums for FZJ80 content")
    parser.add_argument("--index-only", action="store_true", help="Build thread index only (no content)")
    parser.add_argument("--max-threads", type=int, default=None, help="Max threads to scrape content for")
    parser.add_argument("--forum", type=str, default=None,
                        choices=list(IH8MUDScraper.TARGET_FORUMS.keys()),
                        help="Scrape a single forum only")
    parser.add_argument("--no-resume", action="store_true", help="Ignore saved state, start fresh")
    args = parser.parse_args()

    asyncio.run(run_scraper(
        max_threads=args.max_threads,
        target_forum=args.forum,
        index_only=args.index_only,
        resume=not args.no_resume,
    ))


if __name__ == "__main__":
    main()
