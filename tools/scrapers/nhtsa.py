"""NHTSA API scraper for AxleLore.

Fetches recall and complaint data for the Toyota Land Cruiser (1993-1997)
from the public NHTSA Vehicle Safety API.

Usage:
    python -m tools.scrapers.nhtsa
    python -m tools.scrapers.nhtsa --years 1995 1996
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from tools.scrapers.base import BaseScraper, ScrapedDocument

logger = logging.getLogger(__name__)

# NHTSA component name → ChromaDB category
_COMPONENT_CATEGORY: dict[str, str] = {
    "ENGINE AND ENGINE COOLING": "engine",
    "ENGINE": "engine",
    "FUEL SYSTEM": "engine",
    "EXHAUST SYSTEM": "engine",
    "AIR BAGS": "chassis",
    "SERVICE BRAKES": "chassis",
    "SERVICE BRAKES, HYDRAULIC": "chassis",
    "SERVICE BRAKES, AIR": "chassis",
    "PARKING BRAKE": "chassis",
    "SUSPENSION": "chassis",
    "STEERING": "chassis",
    "WHEELS": "chassis",
    "TIRES": "chassis",
    "ELECTRICAL SYSTEM": "electrical",
    "LIGHTING": "electrical",
    "POWER TRAIN": "drivetrain",
    "VEHICLE SPEED CONTROL": "drivetrain",
    "SEAT BELTS": "body",
    "SEATS": "body",
    "STRUCTURE": "body",
    "EXTERIOR LIGHTING": "electrical",
    "INTERIOR LIGHTING": "electrical",
    "VISIBILITY": "body",
    "LATCHES/LOCKS/LINKAGES": "body",
}

YEARS = list(range(1993, 1998))  # 1993-1997

API_BASE = "https://api.nhtsa.gov"


class NHTSAScraper(BaseScraper):
    """Scraper for NHTSA recalls and complaints API."""

    def __init__(
        self,
        output_dir: Path = Path("data/raw/nhtsa"),
        years: list[int] | None = None,
        **kwargs,
    ):
        super().__init__(output_dir, rate_limit=10.0, **kwargs)
        self.years = years or YEARS

    async def scrape(self):
        """Scrape NHTSA recalls and complaints for all target years."""
        for year in self.years:
            for data_type in ("recalls", "complaints"):
                await self._scrape_type(year, data_type)

    async def _scrape_type(self, year: int, data_type: str) -> None:
        if data_type == "recalls":
            url = (
                f"{API_BASE}/recalls/recallsByVehicle"
                f"?make=toyota&model=land%20cruiser&modelYear={year}"
            )
        else:
            url = (
                f"{API_BASE}/complaints/complaintsByVehicle"
                f"?make=toyota&model=land%20cruiser&modelYear={year}"
            )

        logger.info("Fetching NHTSA %s for %d ...", data_type, year)
        body = await self.fetch(url)
        if not body:
            logger.warning("No response for %s %d", data_type, year)
            return

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON for %s %d", data_type, year)
            return

        # Save raw JSON
        self.save_raw(data, f"{year}_{data_type}.json")

        results = data.get("results", [])
        logger.info("  %s %d: %d results", data_type, year, len(results))


async def run_scraper(years: list[int] | None = None) -> Path:
    """Run the NHTSA scraper and return output directory."""
    output_dir = Path("data/raw/nhtsa")
    async with NHTSAScraper(output_dir, years=years) as scraper:
        await scraper.scrape()
    return output_dir


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Scrape NHTSA recalls/complaints for Land Cruiser")
    parser.add_argument(
        "--years", nargs="+", type=int, default=None,
        help="Model years to query (default: 1993-1997)",
    )
    args = parser.parse_args()

    asyncio.run(run_scraper(args.years))
    print("NHTSA scraping complete.  Raw data in data/raw/nhtsa/")


if __name__ == "__main__":
    main()
