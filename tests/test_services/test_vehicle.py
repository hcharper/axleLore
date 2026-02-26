"""Tests for VehicleService."""

import pytest


class TestVehicleService:
    """Unit tests for the vehicle configuration service."""

    def test_load_fzj80_config(self, vehicle_service):
        cfg = vehicle_service.load_config("fzj80")
        assert cfg.vehicle_type == "fzj80"
        assert cfg.name == "Toyota Land Cruiser FZJ80"
        assert 1996 in cfg.production_years
        assert cfg.engine["code"] == "1FZ-FE"

    def test_load_config_cached(self, vehicle_service):
        cfg1 = vehicle_service.load_config("fzj80")
        cfg2 = vehicle_service.load_config("fzj80")
        assert cfg1 is cfg2  # Same instance from cache

    def test_load_config_not_found(self, vehicle_service):
        with pytest.raises(FileNotFoundError):
            vehicle_service.load_config("nonexistent")

    def test_get_supported_vehicles(self, vehicle_service):
        vehicles = vehicle_service.get_supported_vehicles()
        assert len(vehicles) >= 1
        fzj80 = next(v for v in vehicles if v["type"] == "fzj80")
        assert fzj80["name"] == "Toyota Land Cruiser FZJ80"

    def test_get_maintenance_schedule(self, vehicle_service):
        schedules = vehicle_service.get_maintenance_schedule("fzj80")
        assert len(schedules) > 0
        oil = next(s for s in schedules if s["service_type"] == "oil_change")
        assert oil["interval_miles"] == 5000

    def test_build_context_from_config(self, vehicle_service):
        ctx = vehicle_service.build_context_from_config("fzj80", year=1996, mileage=185000)
        assert ctx.vehicle_type == "fzj80"
        assert ctx.vehicle_name == "Toyota Land Cruiser FZJ80"
        assert ctx.year == 1996
        assert ctx.current_mileage == 185000
        assert ctx.engine_code == "1FZ-FE"

    def test_context_to_prompt_string(self, vehicle_service):
        ctx = vehicle_service.build_context_from_config(
            "fzj80", year=1996, mileage=185000, nickname="Big Red"
        )
        prompt = ctx.to_prompt_string()
        assert "1996" in prompt
        assert "Toyota Land Cruiser FZJ80" in prompt
        assert "185,000 mi" in prompt
        assert "Big Red" in prompt
        assert "1FZ-FE" in prompt
