"""Tests for the service records API endpoints."""

import pytest
from datetime import datetime


class TestServiceRecordEndpoints:
    """Test /api/v1/service/* endpoints."""

    def test_get_maintenance_schedule(self, client):
        resp = client.get("/api/v1/service/schedules/fzj80")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vehicle_type"] == "fzj80"
        assert len(data["schedules"]) > 0
        # Oil change should be in there
        types = [s["service_type"] for s in data["schedules"]]
        assert "oil_change" in types

    def test_get_schedule_invalid_vehicle(self, client):
        resp = client.get("/api/v1/service/schedules/nonexistent")
        assert resp.status_code == 404

    def test_service_record_lifecycle(self, client):
        # Create a vehicle first
        v_resp = client.post("/api/v1/vehicles/", json={
            "vehicle_type": "fzj80",
            "nickname": "Service Test",
            "year": 1996,
        })
        assert v_resp.status_code == 201
        vehicle_id = v_resp.json()["id"]

        # Create service record
        resp = client.post(f"/api/v1/service/{vehicle_id}/records", json={
            "service_date": "2024-01-15T10:00:00",
            "service_type": "oil_change",
            "mileage": 185000,
            "description": "Mobil 1 5W-30, Toyota filter",
            "cost": 45.99,
            "performed_by": "self",
        })
        assert resp.status_code == 201
        record_id = resp.json()["id"]

        # List records
        resp = client.get(f"/api/v1/service/{vehicle_id}/records")
        assert resp.status_code == 200
        records = resp.json()
        assert len(records) == 1
        assert records[0]["service_type"] == "oil_change"

        # Delete record
        resp = client.delete(f"/api/v1/service/{vehicle_id}/records/{record_id}")
        assert resp.status_code == 200

        # Verify deleted
        resp = client.get(f"/api/v1/service/{vehicle_id}/records")
        assert resp.json() == []
