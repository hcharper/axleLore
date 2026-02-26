"""Scrapers module initialization."""
from tools.scrapers.base import BaseScraper, ScrapedDocument
from tools.scrapers.state import ScrapeStateManager

# Lazy imports — these scrapers require optional deps (bs4, lxml)


def __getattr__(name: str):
    if name == "IH8MUDScraper":
        from tools.scrapers.ih8mud import IH8MUDScraper
        return IH8MUDScraper
    if name == "NHTSAScraper":
        from tools.scrapers.nhtsa import NHTSAScraper
        return NHTSAScraper
    if name == "SORScraper":
        from tools.scrapers.sor import SORScraper
        return SORScraper
    if name == "WebArticleScraper":
        from tools.scrapers.web_articles import WebArticleScraper
        return WebArticleScraper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseScraper",
    "ScrapedDocument",
    "ScrapeStateManager",
    "IH8MUDScraper",
    "NHTSAScraper",
    "SORScraper",
    "WebArticleScraper",
]
