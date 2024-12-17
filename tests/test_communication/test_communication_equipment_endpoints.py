"""Tests for equipment endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from micro_cold_spray.api.communication.endpoints.equipment import router
from micro_cold_spray.api.communication.service import CommunicationService
from micro_cold_spray.api.base.exceptions import ServiceError
from micro_cold_spray.api.base import _services


@pytest.fixture
def mock_equipment_service():
    """Create mock equipment service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_communication_service(mock_equipment_service):
    """Create mock communication service with equipment service."""
    service = AsyncMock(spec=CommunicationService)
    service.equipment = mock_equipment_service
    return service


@pytest.fixture
def test_app(mock_communication_service):
    """Create test FastAPI app with equipment router."""
    app = FastAPI()
    
    # Initialize service
    _services[CommunicationService] = mock_communication_service
    
    # Mount router without prefix (it's already defined in the router)
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture(autouse=True)
def cleanup_services():
    """Clean up services after each test."""
    yield
    _services.clear()


class TestEquipmentEndpoints:
    """Test equipment endpoint functionality."""

    def test_get_equipment_status_success(self, client, mock_equipment_service):
        """Test successful equipment status retrieval."""
        mock_equipment_service.get_status.return_value = {
            "gas": {
                "main": {"flow": 50.0, "setpoint": 50.0, "valve": True},
                "feeder": {"flow": 5.0, "setpoint": 5.0, "valve": True}
            },
            "pressure": {
                "main": 100.0,
                "feeder": 50.0,
                "nozzle": 75.0,
                "regulator": 80.0,
                "chamber": 0.1
            },
            "vacuum": {
                "gate_valve": {"open": True, "partial": False},
                "shutter": True
            }
        }

        response = client.get("/equipment/status")
        assert response.status_code == 200
        data = response.json()

        assert data["gas"]["main"]["flow"] == 50.0
        assert data["gas"]["feeder"]["valve"] is True
        assert data["pressure"]["nozzle"] == 75.0
        assert data["vacuum"]["shutter"] is True

    def test_get_equipment_status_service_error(self, client, mock_equipment_service):
        """Test equipment status with service error."""
        mock_equipment_service.get_status.side_effect = ServiceError(
            "Failed to get status",
            {"component": "equipment"}
        )

        response = client.get("/equipment/status")
        assert response.status_code == 400
        data = response.json()
        assert "Failed to get status" in data["detail"]["error"]
        assert data["detail"]["context"]["component"] == "equipment"

    def test_get_equipment_status_unexpected_error(self, client, mock_equipment_service):
        """Test equipment status with unexpected error."""
        mock_equipment_service.get_status.side_effect = Exception("Unexpected error")

        response = client.get("/equipment/status")
        assert response.status_code == 500
        data = response.json()
        assert "Unexpected error" == data["detail"]

    def test_set_gas_flow_success(self, client, mock_equipment_service):
        """Test successful gas flow control."""
        request_data = {
            "flow_type": "main",
            "value": 50.0
        }

        response = client.post("/equipment/gas/flow", json=request_data)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_equipment_service.set_gas_flow.assert_called_once_with("main", 50.0)

    def test_set_gas_flow_validation_error(self, client):
        """Test gas flow with invalid request data."""
        # Test invalid flow type
        response = client.post("/equipment/gas/flow", json={
            "flow_type": "invalid",
            "value": 50.0
        })
        assert response.status_code == 422  # Validation error

        # Test invalid value range
        response = client.post("/equipment/gas/flow", json={
            "flow_type": "main",
            "value": 150.0  # Over maximum
        })
        assert response.status_code == 422

    def test_set_gas_flow_service_error(self, client, mock_equipment_service):
        """Test gas flow with service error."""
        mock_equipment_service.set_gas_flow.side_effect = ServiceError(
            "Failed to set flow",
            {"flow_type": "main"}
        )

        response = client.post("/equipment/gas/flow", json={
            "flow_type": "main",
            "value": 50.0
        })
        assert response.status_code == 400
        data = response.json()
        assert "Failed to set flow" in data["detail"]["error"]
        assert data["detail"]["context"]["flow_type"] == "main"

    def test_set_gas_valve_success(self, client, mock_equipment_service):
        """Test successful gas valve control."""
        request_data = {
            "valve": "main",
            "state": True
        }

        response = client.post("/equipment/gas/valve", json=request_data)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_equipment_service.set_gas_valve.assert_called_once_with("main", True)

    def test_set_gas_valve_validation_error(self, client):
        """Test gas valve with invalid request data."""
        # Test invalid valve type
        response = client.post("/equipment/gas/valve", json={
            "valve": "invalid",
            "state": True
        })
        assert response.status_code == 422

    def test_set_vacuum_pump_success(self, client, mock_equipment_service):
        """Test successful vacuum pump control."""
        request_data = {
            "pump": "mechanical",
            "state": True
        }

        response = client.post("/equipment/vacuum/pump", json=request_data)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_equipment_service.control_vacuum_pump.assert_called_once_with("mechanical", True)

    def test_set_vacuum_pump_validation_error(self, client):
        """Test vacuum pump with invalid request data."""
        # Test invalid pump type
        response = client.post("/equipment/vacuum/pump", json={
            "pump": "invalid",
            "state": True
        })
        assert response.status_code == 422

    def test_set_shutter_success(self, client, mock_equipment_service):
        """Test successful shutter control."""
        request_data = {
            "state": True
        }

        response = client.post("/equipment/shutter", json=request_data)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_equipment_service.control_shutter.assert_called_once_with(True)

    def test_set_gate_valve_success(self, client, mock_equipment_service):
        """Test successful gate valve control."""
        request_data = {
            "position": "open"
        }

        response = client.post("/equipment/vacuum/gate", json=request_data)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_equipment_service.control_gate_valve.assert_called_once_with("open")

    def test_set_gate_valve_validation_error(self, client):
        """Test gate valve with invalid request data."""
        # Test invalid position
        response = client.post("/equipment/vacuum/gate", json={
            "position": "invalid"
        })
        assert response.status_code == 422

    def test_set_gate_valve_service_error(self, client, mock_equipment_service):
        """Test gate valve with service error."""
        mock_equipment_service.control_gate_valve.side_effect = ServiceError(
            "Failed to control gate valve",
            {"position": "open"}
        )

        response = client.post("/equipment/vacuum/gate", json={
            "position": "open"
        })
        assert response.status_code == 400
        data = response.json()
        assert "Failed to control gate valve" in data["detail"]["error"]
        assert data["detail"]["context"]["position"] == "open"
