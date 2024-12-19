"""Tests for motion endpoints."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from micro_cold_spray.api.communication.endpoints.motion import router
from micro_cold_spray.api.communication.service import CommunicationService
from micro_cold_spray.api.base.exceptions import ServiceError, ValidationError


@pytest.fixture
def mock_motion_service():
    """Create mock motion service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_communication_service(mock_motion_service):
    """Create mock communication service with motion service."""
    service = AsyncMock(spec=CommunicationService)
    service.motion_service = mock_motion_service
    return service


@pytest.fixture
def test_app(mock_communication_service):
    """Create test FastAPI app with motion router."""
    app = FastAPI()
    app.state.service = mock_communication_service
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestMotionEndpoints:
    """Test motion endpoint functionality."""

    def test_get_axis_status_success(self, client, mock_motion_service):
        """Test successful axis status retrieval."""
        mock_motion_service.get_status.return_value = {
            "position": 100.0,
            "velocity": 50.0,
            "acceleration": 25.0,
            "moving": False,
            "homed": True,
            "error": None
        }

        response = client.get("/motion/status/x")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "ok"
        assert data["axis_id"] == "x"
        assert data["state"]["position"] == 100.0
        assert data["state"]["velocity"] == 50.0
        assert data["state"]["acceleration"] == 25.0
        assert not data["state"]["moving"]
        assert data["state"]["homed"]
        assert data["state"]["error"] is None

    def test_get_axis_status_not_found(self, client, mock_motion_service):
        """Test axis status with validation error."""
        mock_motion_service.get_status.side_effect = ValidationError(
            "Axis not found: invalid"
        )

        response = client.get("/motion/status/invalid")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Axis not found: invalid" in data["detail"]

    def test_get_axis_status_service_error(self, client, mock_motion_service):
        """Test axis status with service error."""
        mock_motion_service.get_status.side_effect = ServiceError(
            "Failed to get status"
        )

        response = client.get("/motion/status/x")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to get status" in data["detail"]

    def test_list_axes_success(self, client, mock_motion_service):
        """Test successful axes list retrieval."""
        mock_motion_service.list_axes.return_value = [
            {
                "id": "x",
                "type": "linear",
                "units": "mm",
                "limits": {"min": 0.0, "max": 1000.0}
            },
            {
                "id": "y",
                "type": "linear",
                "units": "mm",
                "limits": {"min": 0.0, "max": 500.0}
            }
        ]

        response = client.get("/motion/list")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "ok"
        assert len(data["axes"]) == 2
        assert data["axes"][0]["id"] == "x"
        assert data["axes"][1]["id"] == "y"

    def test_list_axes_service_error(self, client, mock_motion_service):
        """Test axes list with service error."""
        mock_motion_service.list_axes.side_effect = ServiceError(
            "Failed to list axes"
        )

        response = client.get("/motion/list")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to list axes" in data["detail"]

    def test_move_axis_success(self, client, mock_motion_service):
        """Test successful axis move."""
        request_data = {
            "axis_id": "x",
            "position": 100.0,
            "velocity": 50.0
        }

        response = client.post("/motion/move", json=request_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Moving axis x to position 100.0"

        mock_motion_service.move_axis.assert_called_once_with(
            axis_id="x",
            position=100.0,
            velocity=50.0
        )

    def test_move_axis_validation_error(self, client, mock_motion_service):
        """Test axis move with validation error."""
        mock_motion_service.move_axis.side_effect = ValidationError(
            "Invalid position: -100.0"
        )

        response = client.post("/motion/move", json={
            "axis_id": "x",
            "position": -100.0,
            "velocity": 50.0
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "Invalid position: -100.0" in data["detail"]

    def test_move_axis_service_error(self, client, mock_motion_service):
        """Test axis move with service error."""
        mock_motion_service.move_axis.side_effect = ServiceError(
            "Failed to move axis"
        )

        response = client.post("/motion/move", json={
            "axis_id": "x",
            "position": 100.0,
            "velocity": 50.0
        })
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to move axis" in data["detail"]

    def test_stop_axis_success(self, client, mock_motion_service):
        """Test successful axis stop."""
        response = client.post("/motion/stop/x")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Stopped axis x"

        mock_motion_service.stop_axis.assert_called_once_with("x")

    def test_stop_axis_not_found(self, client, mock_motion_service):
        """Test axis stop with validation error."""
        mock_motion_service.stop_axis.side_effect = ValidationError(
            "Axis not found: invalid"
        )

        response = client.post("/motion/stop/invalid")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Axis not found: invalid" in data["detail"]

    def test_stop_axis_service_error(self, client, mock_motion_service):
        """Test axis stop with service error."""
        mock_motion_service.stop_axis.side_effect = ServiceError(
            "Failed to stop axis"
        )

        response = client.post("/motion/stop/x")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to stop axis" in data["detail"]
