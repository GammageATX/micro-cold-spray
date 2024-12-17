"""Tests for motion endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from micro_cold_spray.api.communication.endpoints.motion import router
from micro_cold_spray.api.communication.service import CommunicationService
from micro_cold_spray.api.base.exceptions import ServiceError
from micro_cold_spray.api.base import _services


@pytest.fixture
def mock_motion_service():
    """Create mock motion service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_communication_service(mock_motion_service):
    """Create mock communication service with motion service."""
    service = AsyncMock(spec=CommunicationService)
    service.motion = mock_motion_service
    return service


@pytest.fixture
def test_app(mock_communication_service):
    """Create test FastAPI app with motion router."""
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


class TestMotionEndpoints:
    """Test motion endpoint functionality."""

    def test_get_motion_status_success(self, client, mock_motion_service):
        """Test successful motion status retrieval."""
        mock_motion_service.get_status.return_value = {
            "position": {
                "x": 100.0,
                "y": 50.0,
                "z": 25.0
            },
            "moving": {
                "x": False,
                "y": False,
                "z": False
            },
            "complete": {
                "x": True,
                "y": True,
                "z": True
            },
            "status": {
                "x": 0,
                "y": 0,
                "z": 0
            }
        }

        response = client.get("/motion/status")
        assert response.status_code == 200
        data = response.json()

        assert data["position"]["x"] == 100.0
        assert data["position"]["y"] == 50.0
        assert data["position"]["z"] == 25.0
        assert not any(data["moving"].values())
        assert all(data["complete"].values())
        assert all(status == 0 for status in data["status"].values())

    def test_get_motion_status_service_error(self, client, mock_motion_service):
        """Test motion status with service error."""
        mock_motion_service.get_status.side_effect = ServiceError(
            "Failed to get status",
            {"component": "motion"}
        )

        response = client.get("/motion/status")
        assert response.status_code == 400
        data = response.json()
        assert "Failed to get status" in data["detail"]["error"]
        assert data["detail"]["context"]["component"] == "motion"

    def test_get_motion_status_unexpected_error(self, client, mock_motion_service):
        """Test motion status with unexpected error."""
        mock_motion_service.get_status.side_effect = Exception("Unexpected error")

        response = client.get("/motion/status")
        assert response.status_code == 500
        data = response.json()
        assert "Unexpected error" == data["detail"]

    def test_move_axis_success(self, client, mock_motion_service):
        """Test successful single axis move."""
        request_data = {
            "axis": "x",
            "position": 100.0,
            "velocity": 50.0
        }

        response = client.post("/motion/move", json=request_data)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_motion_service.move_axis.assert_called_once_with("x", 100.0, 50.0)

    def test_move_axis_validation_error(self, client):
        """Test single axis move with invalid request data."""
        # Test invalid axis
        response = client.post("/motion/move", json={
            "axis": "invalid",
            "position": 100.0,
            "velocity": 50.0
        })
        assert response.status_code == 422  # Validation error

        # Test invalid position range
        response = client.post("/motion/move", json={
            "axis": "x",
            "position": 2000.0,  # Over maximum
            "velocity": 50.0
        })
        assert response.status_code == 422

        # Test invalid velocity range
        response = client.post("/motion/move", json={
            "axis": "x",
            "position": 100.0,
            "velocity": 150.0  # Over maximum
        })
        assert response.status_code == 422

    def test_move_axis_service_error(self, client, mock_motion_service):
        """Test single axis move with service error."""
        mock_motion_service.move_axis.side_effect = ServiceError(
            "Failed to move axis",
            {"axis": "x"}
        )

        response = client.post("/motion/move", json={
            "axis": "x",
            "position": 100.0,
            "velocity": 50.0
        })
        assert response.status_code == 400
        data = response.json()
        assert "Failed to move axis" in data["detail"]["error"]
        assert data["detail"]["context"]["axis"] == "x"

    def test_move_xy_success(self, client, mock_motion_service):
        """Test successful coordinated XY move."""
        request_data = {
            "x_position": 100.0,
            "y_position": 50.0,
            "velocity": 75.0
        }

        response = client.post("/motion/move/xy", json=request_data)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_motion_service.move_xy.assert_called_once_with(100.0, 50.0, 75.0)

    def test_move_xy_validation_error(self, client):
        """Test coordinated XY move with invalid request data."""
        # Test invalid X position range
        response = client.post("/motion/move/xy", json={
            "x_position": 2000.0,  # Over maximum
            "y_position": 50.0,
            "velocity": 75.0
        })
        assert response.status_code == 422

        # Test invalid Y position range
        response = client.post("/motion/move/xy", json={
            "x_position": 100.0,
            "y_position": 2000.0,  # Over maximum
            "velocity": 75.0
        })
        assert response.status_code == 422

        # Test invalid velocity range
        response = client.post("/motion/move/xy", json={
            "x_position": 100.0,
            "y_position": 50.0,
            "velocity": 150.0  # Over maximum
        })
        assert response.status_code == 422

    def test_move_xy_service_error(self, client, mock_motion_service):
        """Test coordinated XY move with service error."""
        mock_motion_service.move_xy.side_effect = ServiceError(
            "Failed to move XY",
            {"x": 100.0, "y": 50.0}
        )

        response = client.post("/motion/move/xy", json={
            "x_position": 100.0,
            "y_position": 50.0,
            "velocity": 75.0
        })
        assert response.status_code == 400
        data = response.json()
        assert "Failed to move XY" in data["detail"]["error"]
        assert data["detail"]["context"]["x"] == 100.0
        assert data["detail"]["context"]["y"] == 50.0

    def test_home_axes_success(self, client, mock_motion_service):
        """Test successful home axes."""
        response = client.post("/motion/home")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_motion_service.home_axes.assert_called_once()

    def test_home_axes_service_error(self, client, mock_motion_service):
        """Test home axes with service error."""
        mock_motion_service.home_axes.side_effect = ServiceError(
            "Failed to home axes",
            {"component": "motion"}
        )

        response = client.post("/motion/home")
        assert response.status_code == 400
        data = response.json()
        assert "Failed to home axes" in data["detail"]["error"]
        assert data["detail"]["context"]["component"] == "motion"

    def test_stop_motion_success(self, client, mock_motion_service):
        """Test successful stop motion."""
        response = client.post("/motion/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        mock_motion_service.stop_motion.assert_called_once()

    def test_stop_motion_service_error(self, client, mock_motion_service):
        """Test stop motion with service error."""
        mock_motion_service.stop_motion.side_effect = ServiceError(
            "Failed to stop motion",
            {"component": "motion"}
        )

        response = client.post("/motion/stop")
        assert response.status_code == 400
        data = response.json()
        assert "Failed to stop motion" in data["detail"]["error"]
        assert data["detail"]["context"]["component"] == "motion"
