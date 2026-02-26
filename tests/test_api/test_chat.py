"""Tests for the chat API endpoints."""

import json
import pytest


class TestChatEndpoints:
    """Test /api/v1/chat/* endpoints."""

    def test_send_message(self, client):
        """POST /chat/message returns a response with sources."""
        resp = client.post(
            "/api/v1/chat/message",
            json={"message": "What is the oil capacity?"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "sources" in data
        assert "tokens_used" in data
        assert "model" in data
        assert len(data["response"]) > 0

    def test_send_message_empty_rejected(self, client):
        """Empty messages should be rejected by validation."""
        resp = client.post(
            "/api/v1/chat/message",
            json={"message": ""}
        )
        assert resp.status_code == 422

    def test_send_message_too_long_rejected(self, client):
        """Messages over 4000 chars should be rejected."""
        resp = client.post(
            "/api/v1/chat/message",
            json={"message": "x" * 4001}
        )
        assert resp.status_code == 422

    def test_send_message_with_vehicle_id(self, client):
        """Messages can optionally include a vehicle_id."""
        resp = client.post(
            "/api/v1/chat/message",
            json={"message": "What oil do I need?", "vehicle_id": None}
        )
        assert resp.status_code == 200

    def test_stream_endpoint(self, client):
        """POST /chat/message/stream returns SSE events."""
        resp = client.post(
            "/api/v1/chat/message/stream",
            json={"message": "What is the oil capacity?"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        # Parse SSE events
        events = []
        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        # Should have at least one token event and a sources event
        assert len(events) >= 2

    def test_get_history_empty(self, client):
        """GET /chat/history returns empty list initially."""
        resp = client.get("/api/v1/chat/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_delete_history(self, client):
        """DELETE /chat/history succeeds."""
        resp = client.delete("/api/v1/chat/history")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
