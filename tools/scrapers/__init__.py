"""Scrapers module initialization."""
from tools.scrapers.base import BaseScraper, ScrapedDocument
from tools.scrapers.ih8mud import IH8MUDScraper

__all__ = ["BaseScraper", "ScrapedDocument", "IH8MUDScraper"]
