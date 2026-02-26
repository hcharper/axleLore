"""Tests for the vehicles API endpoints."""

import pytest


class TestVehicleEndpoints:
    """Test /api/v1/vehicles/* endpoints."""

    def test_list_vehicles_empty(self, client):
        resp = client.get("/api/v1/vehicles/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_vehicle_types(self, client):
        resp = client.get("/api/v1/vehicles/types")
        assert resp.status_code == 200
        types = resp.json()
        assert len(types) >= 1
        assert any(v["type"] == "fzj80" for v in types)

    def test_create_vehicle(self, client):
        resp = client.post("/api/v1/vehicles/", json={
            "vehicle_type": "fzj80",
            "nickname": "Big Red",
            "year": 1996,
            "current_mileage": 185000,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["vehicle_type"] == "fzj80"
        assert data["nickname"] == "Big Red"
        assert data["year"] == 1996
        assert data["id"] is not None

    def test_create_vehicle_invalid_type(self, client):
        resp = client.post("/api/v1/vehicles/", json={
            "vehicle_type": "nonexistent",
        })
        assert resp.status_code == 400

    def test_vehicle_crud_lifecycle(self, client):
        # Create
        resp = client.post("/api/v1/vehicles/", json={
            "vehicle_type": "fzj80",
            "nickname": "Test Cruiser",
            "year": 1995,
        })
        assert resp.status_code == 201
        vehicle_id = resp.json()["id"]

        # Get
        resp = client.get(f"/api/v1/vehicles/{vehicle_id}")
        assert resp.status_code == 200
        assert resp.json()["nickname"] == "Test Cruiser"

        # Update
        resp = client.put(f"/api/v1/vehicles/{vehicle_id}", json={
            "nickname": "Updated Cruiser",
            "current_mileage": 200000,
        })
        assert resp.status_code == 200
        assert resp.json()["nickname"] == "Updated Cruiser"

        # Delete
        resp = client.delete(f"/api/v1/vehicles/{vehicle_id}")
        assert resp.status_code == 200

        # Verify deleted
        resp = client.get(f"/api/v1/vehicles/{vehicle_id}")
        assert resp.status_code == 404
