"""Tests for equipment endpoints."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from micro_cold_spray.api.communication.endpoints.equipment import router
from micro_cold_spray.api.communication.service import CommunicationService
from micro_cold_spray.api.base.exceptions import ServiceError, ValidationError


@pytest.fixture
def mock_equipment_service():
    """Create mock equipment service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_communication_service(mock_equipment_service):
    """Create mock communication service with equipment service."""
    service = AsyncMock(spec=CommunicationService)
    service.equipment_service = mock_equipment_service
    return service


@pytest.fixture
def test_app(mock_communication_service):
    """Create test FastAPI app with equipment router."""
    app = FastAPI()
    app.state.service = mock_communication_service
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


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

        response = client.get("/equipment/status/main")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "ok"
        assert data["equipment_id"] == "main"
        assert data["state"]["gas"]["main"]["flow"] == 50.0
        assert data["state"]["gas"]["feeder"]["valve"] is True
        assert data["state"]["pressure"]["nozzle"] == 75.0
        assert data["state"]["vacuum"]["shutter"] is True

    def test_get_equipment_status_not_found(self, client, mock_equipment_service):
        """Test equipment status with validation error."""
        mock_equipment_service.get_status.side_effect = ValidationError(
            "Equipment not found: invalid"
        )

        response = client.get("/equipment/status/invalid")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Equipment not found: invalid" in data["detail"]

    def test_get_equipment_status_service_error(self, client, mock_equipment_service):
        """Test equipment status with service error."""
        mock_equipment_service.get_status.side_effect = ServiceError(
            "Failed to get status"
        )

        response = client.get("/equipment/status/main")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to get status" in data["detail"]

    def test_get_equipment_status_unexpected_error(self, client, mock_equipment_service):
        """Test equipment status with unexpected error."""
        mock_equipment_service.get_status.side_effect = Exception("Unexpected error")

        response = client.get("/equipment/status/main")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Unexpected error" == data["detail"]

    def test_set_gas_flow_success(self, client, mock_equipment_service):
        """Test successful gas flow control."""
        request_data = {
            "flow_type": "main",
            "value": 50.0
        }

        response = client.post("/equipment/gas/flow", json=request_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Gas flow main set to 50.0"

        mock_equipment_service.set_gas_flow.assert_called_once_with(
            flow_type="main",
            value=50.0
        )

    def test_set_gas_flow_validation_error(self, client, mock_equipment_service):
        """Test gas flow with validation error."""
        mock_equipment_service.set_gas_flow.side_effect = ValidationError(
            "Invalid flow value: 150.0"
        )

        response = client.post("/equipment/gas/flow", json={
            "flow_type": "main",
            "value": 150.0
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "Invalid flow value: 150.0" in data["detail"]

    def test_set_gas_flow_service_error(self, client, mock_equipment_service):
        """Test gas flow with service error."""
        mock_equipment_service.set_gas_flow.side_effect = ServiceError(
            "Failed to set flow"
        )

        response = client.post("/equipment/gas/flow", json={
            "flow_type": "main",
            "value": 50.0
        })
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to set flow" in data["detail"]

    def test_set_valve_state_success(self, client, mock_equipment_service):
        """Test successful valve control."""
        response = client.post("/equipment/valve/main/state?state=true")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Valve main opened"

        mock_equipment_service.set_valve_state.assert_called_once_with("main", True)

    def test_set_valve_state_not_found(self, client, mock_equipment_service):
        """Test valve control with validation error."""
        mock_equipment_service.set_valve_state.side_effect = ValidationError(
            "Valve not found: invalid"
        )

        response = client.post("/equipment/valve/invalid/state?state=true")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Valve not found: invalid" in data["detail"]

    def test_set_valve_state_service_error(self, client, mock_equipment_service):
        """Test valve control with service error."""
        mock_equipment_service.set_valve_state.side_effect = ServiceError(
            "Failed to set valve state"
        )

        response = client.post("/equipment/valve/main/state?state=true")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to set valve state" in data["detail"]
