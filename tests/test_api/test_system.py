"""Tests for system and health endpoints."""

import pytest


class TestSystemEndpoints:
    """Test health, info, and system endpoints."""

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert "llm" in data["services"]

    def test_api_info(self, client):
        resp = client.get("/api/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["app_name"] == "RigSherpa"
        assert "endpoints" in data
        assert "chat_stream" in data["endpoints"]

    def test_kb_status(self, client):
        resp = client.get("/api/v1/kb/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_chunks" in data
        assert "collections" in data

    def test_system_version(self, client):
        resp = client.get("/api/v1/system/version")
        assert resp.status_code == 200
        data = resp.json()
        assert "software_version" in data
        assert "model" in data

    def test_obd2_status_disabled(self, client):
        resp = client.get("/api/v1/obd2/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
