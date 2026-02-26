"""Curated web article scraper for AxleLore.

Fetches and extracts main content from a hardcoded list of high-value
FZJ80 technical articles using BeautifulSoup.

Usage:
    python -m tools.scrapers.web_articles
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup

from tools.scrapers.base import BaseScraper, ScrapedDocument

logger = logging.getLogger(__name__)

# Curated high-value URLs with category assignments
ARTICLE_SOURCES: list[dict] = [
    {
        "url": "https://sleeoffroad.com/tech-zone/80-series-newbie-guide/",
        "categories": ["general", "forum_mods"],
        "title_hint": "80 Series Newbie Guide",
    },
    {
        "url": "https://roughtrax4x4.com/blog/land-cruiser-fzj80-1992-1998-vehicle-specifications/",
        "categories": ["general"],
        "title_hint": "FZJ80 Vehicle Specifications",
    },
    {
        "url": "https://xatracing.com/jdm-land-cruiser-80-series-quick-info.html",
        "categories": ["general", "drivetrain"],
        "title_hint": "JDM Land Cruiser 80 Series Quick Info",
    },
    {
        "url": "https://engine-specs.net/toyota/1fz-fe.html",
        "categories": ["engine"],
        "title_hint": "Toyota 1FZ-FE Engine Specs",
    },
]


def _slugify(url: str) -> str:
    """Create a filesystem-safe slug from a URL."""
    slug = re.sub(r"https?://", "", url)
    slug = re.sub(r"[^\w\-]", "_", slug)
    return slug[:80].strip("_")


def _extract_main_content(html: str) -> tuple[str, str]:
    """Extract title and main text content from HTML, stripping nav/ads/footers.

    Returns (title, text_content).
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove noise elements
    for tag in soup.find_all(["nav", "header", "footer", "aside", "script", "style", "noscript"]):
        tag.decompose()
    for tag in soup.find_all(class_=re.compile(r"nav|menu|sidebar|footer|advert|cookie|popup", re.I)):
        tag.decompose()

    # Extract title
    title_tag = soup.find("title")
    h1 = soup.find("h1")
    title = ""
    if h1:
        title = h1.get_text(strip=True)
    elif title_tag:
        title = title_tag.get_text(strip=True)

    # Try to find the main content area
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(class_=re.compile(r"content|entry|post|article", re.I))
        or soup.find("body")
    )
    if main is None:
        main = soup

    text = main.get_text(separator="\n", strip=True)

    # Collapse excessive whitespace while preserving paragraph breaks
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return title, text.strip()


def _split_by_headings(html: str) -> list[dict]:
    """Split HTML content into sections by heading tags.

    Returns list of {heading, content} dicts.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove noise
    for tag in soup.find_all(["nav", "header", "footer", "aside", "script", "style", "noscript"]):
        tag.decompose()

    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(class_=re.compile(r"content|entry|post|article", re.I))
        or soup.find("body")
    )
    if main is None:
        main = soup

    sections: list[dict] = []
    current_heading = ""
    current_parts: list[str] = []

    for elem in main.find_all(True):
        if elem.name in ("h1", "h2", "h3"):
            # Save previous section
            if current_parts:
                text = "\n".join(current_parts).strip()
                if len(text) > 50:
                    sections.append({"heading": current_heading, "content": text})
            current_heading = elem.get_text(strip=True)
            current_parts = []
        elif elem.name in ("p", "li", "td", "pre", "blockquote"):
            txt = elem.get_text(strip=True)
            if txt:
                current_parts.append(txt)

    # Final section
    if current_parts:
        text = "\n".join(current_parts).strip()
        if len(text) > 50:
            sections.append({"heading": current_heading, "content": text})

    return sections


class WebArticleScraper(BaseScraper):
    """Scraper for curated FZJ80 technical web articles."""

    def __init__(self, output_dir: Path = Path("data/raw/web"), **kwargs):
        super().__init__(output_dir, rate_limit=3.0, **kwargs)

    async def scrape(self):
        """Fetch all curated articles."""
        for article in ARTICLE_SOURCES:
            url = article["url"]
            slug = _slugify(url)
            logger.info("Fetching: %s", url)

            html = await self.fetch(url)
            if not html:
                logger.warning("Failed to fetch: %s", url)
                continue

            title, text = _extract_main_content(html)
            if not title:
                title = article.get("title_hint", slug)

            sections = _split_by_headings(html)

            raw = {
                "url": url,
                "title": title,
                "categories": article["categories"],
                "full_text": text,
                "sections": sections,
            }
            self.save_raw(raw, f"{slug}.json")
            logger.info("  Saved %s (%d chars, %d sections)", slug, len(text), len(sections))


async def run_scraper() -> Path:
    """Run the web article scraper and return output directory."""
    output_dir = Path("data/raw/web")
    async with WebArticleScraper(output_dir) as scraper:
        await scraper.scrape()
    return output_dir


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    asyncio.run(run_scraper())
    print("Web article scraping complete.  Raw data in data/raw/web/")


if __name__ == "__main__":
    main()
