"""Scrape state manager for RigSherpa — resume support for long-running scrapers.

Backs state to a SQLite database so scrapers can stop and resume without
re-crawling already-seen pages and items.

Usage:
    state = ScrapeStateManager("data/raw/scrape_state.db")
    page = state.get_resume_page("ih8mud_80_series_tech")  # 0 if fresh

    for page_num in range(page, total_pages):
        for thread_id in scrape_page(page_num):
            if state.is_item_done("ih8mud", thread_id):
                continue
            scrape_thread(thread_id)
            state.mark_item_done("ih8mud", thread_id)
        state.mark_page_done("ih8mud_80_series_tech", page_num)
"""

from __future__ import annotations

import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS progress (
    scraper_name  TEXT PRIMARY KEY,
    last_page     INTEGER NOT NULL DEFAULT 0,
    completed_items INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'idle',
    last_run      TEXT
);

CREATE TABLE IF NOT EXISTS items (
    scraper_name  TEXT NOT NULL,
    item_id       TEXT NOT NULL,
    scraped_at    TEXT NOT NULL,
    PRIMARY KEY (scraper_name, item_id)
);
"""


class ScrapeStateManager:
    """SQLite-backed scrape checkpoint manager."""

    def __init__(self, db_path: str | Path = "data/raw/scrape_state.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ── page tracking ─────────────────────────────────────────

    def mark_page_done(self, scraper_name: str, page: int) -> None:
        """Record that *page* has been fully scraped."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO progress (scraper_name, last_page, completed_items, status, last_run)
            VALUES (?, ?, 0, 'running', ?)
            ON CONFLICT(scraper_name) DO UPDATE SET
                last_page = MAX(last_page, excluded.last_page),
                status = 'running',
                last_run = excluded.last_run
            """,
            (scraper_name, page, now),
        )
        self._conn.commit()

    def get_resume_page(self, scraper_name: str) -> int:
        """Return the page number to resume from (0 if never run)."""
        row = self._conn.execute(
            "SELECT last_page FROM progress WHERE scraper_name = ?",
            (scraper_name,),
        ).fetchone()
        if row is None:
            return 0
        # Resume from the page *after* the last completed one
        return row[0] + 1

    # ── item tracking ─────────────────────────────────────────

    def mark_item_done(self, scraper_name: str, item_id: str) -> None:
        """Record that *item_id* has been scraped."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT OR IGNORE INTO items (scraper_name, item_id, scraped_at) VALUES (?, ?, ?)",
            (scraper_name, item_id, now),
        )
        # Bump the counter on progress
        self._conn.execute(
            """
            INSERT INTO progress (scraper_name, last_page, completed_items, status, last_run)
            VALUES (?, 0, 1, 'running', ?)
            ON CONFLICT(scraper_name) DO UPDATE SET
                completed_items = completed_items + 1,
                last_run = excluded.last_run
            """,
            (scraper_name, now),
        )
        self._conn.commit()

    def is_item_done(self, scraper_name: str, item_id: str) -> bool:
        """Check whether *item_id* has already been scraped."""
        row = self._conn.execute(
            "SELECT 1 FROM items WHERE scraper_name = ? AND item_id = ?",
            (scraper_name, item_id),
        ).fetchone()
        return row is not None

    # ── status helpers ────────────────────────────────────────

    def set_status(self, scraper_name: str, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO progress (scraper_name, last_page, completed_items, status, last_run)
            VALUES (?, 0, 0, ?, ?)
            ON CONFLICT(scraper_name) DO UPDATE SET
                status = excluded.status,
                last_run = excluded.last_run
            """,
            (scraper_name, status, now),
        )
        self._conn.commit()

    def get_stats(self) -> dict[str, dict]:
        """Return stats for every scraper that has run."""
        rows = self._conn.execute(
            "SELECT scraper_name, last_page, completed_items, status, last_run FROM progress"
        ).fetchall()
        return {
            row[0]: {
                "last_page": row[1],
                "completed_items": row[2],
                "status": row[3],
                "last_run": row[4],
            }
            for row in rows
        }

    def get_scraper_item_count(self, scraper_name: str) -> int:
        """Return total items scraped for a given scraper."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM items WHERE scraper_name = ?",
            (scraper_name,),
        ).fetchone()
        return row[0] if row else 0
