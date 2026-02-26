"""Tests for the document chunker."""

import pytest
from tools.kb_builder.chunker import SmartChunker


class TestSmartChunker:
    """Test all chunking strategies."""

    @pytest.fixture
    def chunker(self):
        return SmartChunker(chunk_size=500, chunk_overlap=50, min_chunk_size=50)

    def test_empty_content_skipped(self, chunker):
        doc = {"source": "fsm", "content": "short", "category": "engine"}
        chunks = chunker.chunk_document(doc)
        assert chunks == []

    def test_fsm_procedure_chunking(self, chunker):
        doc = {
            "source": "fsm",
            "title": "Oil Change Procedure",
            "source_id": "lu-3",
            "content": """
1. Warm engine to operating temperature.
2. Place drain pan under oil drain plug.
3. Remove drain plug (27 ft-lbs torque on reinstall).
4. Allow oil to drain completely (approx 10 minutes).
5. Replace drain plug with new washer.
6. Remove and replace oil filter (90915-YZZB6).
7. Add 6.8 quarts of 5W-30 oil.
8. Start engine and check for leaks.
9. Check oil level after 5 minutes and top off.
""".strip(),
            "category": "engine",
        }
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1
        assert all(c.category == "engine" for c in chunks)
        assert all(c.source == "fsm" for c in chunks)
        # Title should be in chunks
        assert any("Oil Change Procedure" in c.text for c in chunks)

    def test_forum_qa_chunking(self, chunker):
        doc = {
            "source": "ih8mud",
            "source_id": "12345",
            "title": "Head gasket replacement tips?",
            "content": """Question: Head gasket replacement tips?

I'm about to tackle a head gasket replacement on my 1995 FZJ80.
Any tips from those who have done it?

Response: Make sure you have the right torque specs. The 1FZ-FE
head bolts need to be torqued to 29 ft-lbs first pass, then 90 degrees.
Use new head bolts, they're torque-to-yield.

Response: Also check the head for warpage before reinstalling.
Maximum warpage spec is 0.05mm. Get it resurfaced if needed.""",
            "category": "engine",
        }
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1
        # Forum chunks should include the topic
        assert any("Head gasket" in c.text for c in chunks)

    def test_general_chunking(self, chunker):
        doc = {
            "source": "other",
            "source_id": "misc-1",
            "content": "The Toyota Land Cruiser FZJ80 is a legendary off-road vehicle. " * 20,
            "category": "general",
        }
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1
        assert all(c.category == "general" for c in chunks)

    def test_chunk_ids_unique(self, chunker):
        doc = {
            "source": "fsm",
            "source_id": "test",
            "content": "First sentence here. " * 30 + "Second sentence here. " * 30,
            "category": "engine",
        }
        chunks = chunker.chunk_document(doc)
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))  # All unique

    def test_parts_chunking(self, chunker):
        doc = {
            "source": "parts",
            "source_id": "catalog-1",
            "content": "Part 90915-YZZB6: Oil filter for 1FZ-FE engine. " * 15,
            "category": "parts",
        }
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1
        assert all(c.source == "parts" for c in chunks)
