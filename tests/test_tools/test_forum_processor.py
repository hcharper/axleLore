"""Tests for the forum post normalizer."""

import json
import pytest
from pathlib import Path
from tools.processors.forum import (
    normalize_thread, compute_quality_score, map_category,
    deduplicate, _clean_post_content,
)


@pytest.fixture
def sample_thread():
    return {
        "thread_id": "123456",
        "title": "Head gasket replacement tips?",
        "url": "https://forum.ih8mud.com/threads/123456/",
        "author": "cruiser_guy",
        "date": "2023-01-15",
        "category": "80-Series Tech",
        "posts": [
            {
                "author": "cruiser_guy",
                "date": "2023-01-15",
                "content": "I'm about to tackle a head gasket replacement on my 1995 FZJ80. Any tips?",
                "votes": 5,
                "is_op": True,
            },
            {
                "author": "tech_expert",
                "date": "2023-01-16",
                "content": "Make sure you torque the head bolts to 29 ft-lbs first pass, then 90 degrees. Use new bolts, they're TTY.",
                "votes": 25,
                "is_op": False,
            },
            {
                "author": "weekend_wrench",
                "date": "2023-01-16",
                "content": "Check head warpage before reinstalling. Max spec is 0.05mm.",
                "votes": 12,
                "is_op": False,
            },
        ],
        "views": 8500,
        "replies": 15,
    }


class TestForumProcessor:

    def test_normalize_thread(self, sample_thread):
        doc = normalize_thread(sample_thread)
        assert doc is not None
        assert doc["source"] == "ih8mud"
        assert doc["source_id"] == "123456"
        assert doc["title"] == "Head gasket replacement tips?"
        assert "torque" in doc["content"].lower()
        assert doc["category"] in ("forum_troubleshoot", "forum_maintenance", "forum_mods")

    def test_normalize_empty_thread(self):
        assert normalize_thread({"title": "", "posts": []}) is None
        assert normalize_thread({"title": "Test", "posts": []}) is None

    def test_quality_score_range(self, sample_thread):
        score = compute_quality_score(sample_thread)
        assert 0.0 <= score <= 1.0
        assert score > 0.3  # Good thread should score well

    def test_quality_score_low_engagement(self):
        thread = {
            "posts": [{"content": "x" * 60, "votes": 0, "is_op": True}],
            "views": 10,
            "replies": 0,
        }
        score = compute_quality_score(thread)
        assert score < 0.3

    def test_category_mapping(self):
        assert map_category("80-Series Tech") == "forum_troubleshoot"
        assert map_category("80-Series Build Threads") == "forum_mods"
        assert map_category("Maintenance") == "forum_maintenance"
        assert map_category("unknown", "install a lift kit") == "forum_mods"
        assert map_category("unknown", "oil change tips") == "forum_maintenance"

    def test_clean_post_content(self):
        content = "[quote]Some quoted text[/quote]\nActual content here."
        cleaned = _clean_post_content(content)
        assert "[quote]" not in cleaned
        assert "Actual content" in cleaned

    def test_deduplicate(self):
        docs = [
            {"title": "Test", "content": "Same content here" * 10, "source_id": "1"},
            {"title": "Test", "content": "Same content here" * 10, "source_id": "2"},
            {"title": "Different", "content": "Totally different stuff" * 10, "source_id": "3"},
        ]
        unique = deduplicate(docs)
        assert len(unique) == 2

    def test_responses_sorted_by_votes(self, sample_thread):
        doc = normalize_thread(sample_thread)
        # The highest-voted response should appear first
        assert "29 ft-lbs" in doc["content"]  # 25 votes
        content_parts = doc["content"].split("Response")
        # tech_expert (25 votes) should come before weekend_wrench (12 votes)
        idx_torque = doc["content"].index("29 ft-lbs")
        idx_warpage = doc["content"].index("warpage")
        assert idx_torque < idx_warpage
