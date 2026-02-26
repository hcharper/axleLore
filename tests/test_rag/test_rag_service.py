"""Tests for RAG service: retrieval, routing, context assembly."""

import pytest
from pathlib import Path


class TestRAGService:
    """Integration tests for RAG retrieval with ephemeral ChromaDB."""

    def test_ensure_collections(self, rag_service):
        collections = rag_service.ensure_collections("fzj80")
        assert "engine" in collections
        assert "drivetrain" in collections
        assert "electrical" in collections
        assert "chassis" in collections
        assert "forum_troubleshoot" in collections
        assert "general" in collections
        assert len(collections) == 11

    def test_get_stats_empty(self, rag_service):
        rag_service.ensure_collections("fzj80")
        stats = rag_service.get_stats("fzj80")
        assert stats["total_chunks"] == 0
        assert stats["vehicle_type"] == "fzj80"

    def test_retrieve_empty_db(self, rag_service):
        rag_service.ensure_collections("fzj80")
        results = rag_service.retrieve("oil capacity", "fzj80")
        assert results == []

    def test_assemble_context_empty(self, rag_service):
        rag_service.ensure_collections("fzj80")
        ctx = rag_service.assemble_context(
            "oil capacity", "fzj80",
            vehicle_context="Vehicle: 1996 FZJ80",
        )
        assert ctx.vehicle_context == "Vehicle: 1996 FZJ80"
        assert len(ctx.chunks) == 0
        assert "YOUR VEHICLE" in ctx.formatted

    def test_seed_and_retrieve(self, rag_service):
        """Seed data then verify retrieval returns relevant chunks."""
        collections = rag_service.ensure_collections("fzj80")

        # Manually add a chunk
        engine_col = collections["engine"]
        embedding = rag_service.embedder.encode(
            ["The 1FZ-FE engine oil capacity is 6.8 quarts with filter."]
        )[0].tolist()

        engine_col.add(
            ids=["test_oil_1"],
            documents=["The 1FZ-FE engine oil capacity is 6.8 quarts with filter."],
            embeddings=[embedding],
            metadatas=[{"source": "fsm", "source_id": "lu-3", "category": "engine"}],
        )

        # Verify stats
        stats = rag_service.get_stats("fzj80")
        assert stats["collections"]["engine"] == 1

        # Retrieve
        results = rag_service.retrieve("How much oil does the 1FZ take?", "fzj80")
        assert len(results) >= 1
        assert "6.8 quarts" in results[0].text

    def test_keyword_routing_engine(self, rag_service):
        """Engine keywords should route to engine collections."""
        routes = rag_service._route_query("engine overheating", "fzj80")
        assert "engine" in routes
        assert "forum_troubleshoot" in routes

    def test_keyword_routing_drivetrain(self, rag_service):
        routes = rag_service._route_query("birfield cv joint noise", "fzj80")
        assert "drivetrain" in routes

    def test_keyword_routing_fallback(self, rag_service):
        """Unknown queries fall back to default collections."""
        routes = rag_service._route_query("how does this thing work", "fzj80")
        assert "engine" in routes or "general" in routes
