"""Specter Off-Road (SOR) parts catalog scraper for RigSherpa.

Scrapes the sor.com 80-series catalog to extract part numbers,
descriptions, fitment, and pricing.

Usage:
    python -m tools.scrapers.sor
    python -m tools.scrapers.sor --max-pages 10
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

BASE_URL = "https://www.sor.com"

# Map SOR catalog section names → system grouping for parts
_SECTION_SYSTEM: dict[str, str] = {
    "axle": "front_axle",
    "front axle": "front_axle",
    "rear axle": "rear_axle",
    "birfield": "front_axle",
    "knuckle": "front_axle",
    "hub": "front_axle",
    "steering": "steering",
    "brake": "brakes",
    "suspension": "suspension",
    "spring": "suspension",
    "shock": "suspension",
    "engine": "engine",
    "cooling": "engine",
    "exhaust": "engine",
    "transmission": "transmission",
    "transfer": "transfer_case",
    "body": "body",
    "interior": "interior",
    "electrical": "electrical",
    "bumper": "bumper_armor",
    "armor": "bumper_armor",
    "roof rack": "accessories",
    "light": "lighting",
}


def _guess_system(category_name: str) -> str:
    """Map a SOR category name to a system group."""
    lower = category_name.lower()
    for keyword, system in _SECTION_SYSTEM.items():
        if keyword in lower:
            return system
    return "general"


class SORScraper(BaseScraper):
    """Scraper for Specter Off-Road 80-series parts catalog."""

    CATALOG_ROOT = f"{BASE_URL}/80serieslandcruiser/"

    def __init__(
        self,
        output_dir: Path = Path("data/raw/sor"),
        max_pages: int = 50,
        **kwargs,
    ):
        super().__init__(output_dir, rate_limit=3.0, **kwargs)
        self.max_pages = max_pages

    async def scrape(self):
        """Discover category pages and extract parts."""
        logger.info("Fetching SOR catalog root: %s", self.CATALOG_ROOT)
        html = await self.fetch(self.CATALOG_ROOT)
        if not html:
            logger.error("Failed to fetch SOR catalog root")
            return

        category_links = self._discover_categories(html)
        logger.info("Found %d category links", len(category_links))

        pages_scraped = 0
        for cat_name, cat_url in category_links:
            if pages_scraped >= self.max_pages:
                break

            logger.info("Scraping category: %s", cat_name)
            cat_html = await self.fetch(cat_url)
            if not cat_html:
                continue

            parts = self._extract_parts(cat_html, cat_name)
            if parts:
                slug = re.sub(r"[^\w]", "_", cat_name.lower()).strip("_")
                self.save_raw({"category": cat_name, "url": cat_url, "parts": parts}, f"{slug}.json")
                logger.info("  %s: %d parts", cat_name, len(parts))

            pages_scraped += 1

    def _discover_categories(self, html: str) -> list[tuple[str, str]]:
        """Extract category page links from the catalog root."""
        soup = BeautifulSoup(html, "lxml")
        links: list[tuple[str, str]] = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if not text or len(text) < 3:
                continue
            # SOR category links are relative paths under the catalog root
            if href.startswith("/") and "80series" in href.lower():
                full_url = f"{BASE_URL}{href}"
                links.append((text, full_url))
            elif href.startswith(self.CATALOG_ROOT):
                links.append((text, href))

        # Deduplicate by URL
        seen: set[str] = set()
        unique: list[tuple[str, str]] = []
        for name, url in links:
            if url not in seen:
                seen.add(url)
                unique.append((name, url))

        return unique

    def _extract_parts(self, html: str, category_name: str) -> list[dict]:
        """Extract part data from a category page."""
        soup = BeautifulSoup(html, "lxml")
        parts: list[dict] = []

        # SOR product pages typically use table rows or product divs
        # Try table-based layout first
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            text = " ".join(c.get_text(strip=True) for c in cells)
            # Look for part number patterns (SOR-XXXX or OEM numeric)
            pn_match = re.search(r"(SOR[\-\s]?\w+|\b\d{5,}\b)", text)

            # Look for price patterns
            price_match = re.search(r"\$[\d,]+\.?\d*", text)

            if pn_match:
                part = {
                    "part_number": pn_match.group(1).strip(),
                    "description": cells[0].get_text(strip=True) if cells else "",
                    "price": price_match.group(0) if price_match else "",
                    "category": category_name,
                    "system": _guess_system(category_name),
                }
                parts.append(part)

        # Fallback: extract from any product-like containers
        if not parts:
            for elem in soup.find_all(class_=re.compile(r"product|item|part", re.I)):
                title_el = elem.find(["h2", "h3", "h4", "strong", "b"])
                title = title_el.get_text(strip=True) if title_el else ""
                desc = elem.get_text(strip=True)
                price_match = re.search(r"\$[\d,]+\.?\d*", desc)
                pn_match = re.search(r"(SOR[\-\s]?\w+|\b\d{5,}\b)", desc)

                if title or pn_match:
                    parts.append({
                        "part_number": pn_match.group(1).strip() if pn_match else "",
                        "description": title or desc[:200],
                        "price": price_match.group(0) if price_match else "",
                        "category": category_name,
                        "system": _guess_system(category_name),
                    })

        return parts


async def run_scraper(max_pages: int = 50) -> Path:
    """Run the SOR scraper and return output directory."""
    output_dir = Path("data/raw/sor")
    async with SORScraper(output_dir, max_pages=max_pages) as scraper:
        await scraper.scrape()
    return output_dir


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Scrape SOR 80-series parts catalog")
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum category pages to scrape")
    args = parser.parse_args()

    asyncio.run(run_scraper(args.max_pages))
    print("SOR scraping complete.  Raw data in data/raw/sor/")


if __name__ == "__main__":
    main()
