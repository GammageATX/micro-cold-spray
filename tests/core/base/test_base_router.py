"""Tests for base router functionality."""

import pytest
from unittest.mock import AsyncMock
from fastapi import FastAPI, status, HTTPException
from fastapi.testclient import TestClient

from micro_cold_spray.api.base.router import add_health_endpoints, get_service_from_app
from micro_cold_spray.api.base import BaseService, ConfigurableService
from tests.utils import assert_error_response, assert_health_response


@pytest.fixture
def mock_base_service():
    """Create a mock base service."""
    service = AsyncMock(spec=BaseService)
    service._service_name = "TestService"
    return service


@pytest.fixture
def app_with_service(mock_base_service):
    """Create FastAPI app with mock service."""
    app = FastAPI()
    app.state.service = mock_base_service
    router = app.router
    add_health_endpoints(router, mock_base_service)
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint functionality."""
    
    def test_health_check_success(self, app_with_service, mock_base_service):
        """Test successful health check."""
        mock_base_service.check_health.return_value = {
            "status": "ok",
            "message": "Service is healthy",
            "service_info": {
                "name": "TestService",
                "version": "1.0.0",
                "running": True,
                "uptime": "0:00:00"
            }
        }
        response = app_with_service.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert_health_response(data, "TestService")
        assert data["status"] == "ok"
        
    def test_health_check_error(self, app_with_service, mock_base_service):
        """Test health check with error."""
        mock_base_service.check_health.side_effect = Exception("Service error")
        response = app_with_service.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Service error" in response.json()["detail"]
        
    def test_health_check_degraded(self, app_with_service, mock_base_service):
        """Test health check with degraded status."""
        mock_base_service.check_health.return_value = {
            "status": "degraded",
            "message": "Performance degraded",
            "service_info": {
                "name": "TestService",
                "version": "1.0.0",
                "running": True,
                "uptime": "0:00:00"
            }
        }
        response = app_with_service.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert_health_response(data, "TestService")
        assert data["status"] == "degraded"

    def test_health_check_warning(self, app_with_service, mock_base_service):
        """Test health check with warning status but service running."""
        mock_base_service.check_health.return_value = {
            "status": "warning",
            "message": "Resource usage high",
            "service_info": {
                "name": "TestService",
                "version": "1.0.0",
                "running": True,
                "uptime": "0:00:00"
            }
        }
        response = app_with_service.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert_health_response(data, "TestService")
        assert data["status"] == "warning"

    def test_health_check_not_running(self, app_with_service, mock_base_service):
        """Test health check when service is not running."""
        mock_base_service.check_health.return_value = {
            "status": "stopped",
            "message": "Service stopped",
            "service_info": {
                "name": "TestService",
                "version": "1.0.0",
                "running": False,
                "uptime": "0:00:00"
            }
        }
        response = app_with_service.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Service is not running" in response.json()["detail"]


class TestControlEndpoint:
    """Test control endpoint functionality."""
    
    def test_control_start(self, app_with_service, mock_base_service):
        """Test start command."""
        response = app_with_service.post("/control", json={"command": "start"})
        assert response.status_code == status.HTTP_200_OK
        mock_base_service.start.assert_called_once()
        
    def test_control_stop(self, app_with_service, mock_base_service):
        """Test stop command."""
        response = app_with_service.post("/control", json={"command": "stop"})
        assert response.status_code == status.HTTP_200_OK
        mock_base_service.stop.assert_called_once()
        
    def test_control_restart(self, app_with_service, mock_base_service):
        """Test restart command."""
        response = app_with_service.post("/control", json={"command": "restart"})
        assert response.status_code == status.HTTP_200_OK
        mock_base_service.restart.assert_called_once()
        
    def test_control_invalid_action(self, app_with_service):
        """Test invalid control command."""
        response = app_with_service.post("/control", json={"command": "invalid"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid command" in response.json()["detail"]
        
    def test_control_error(self, app_with_service, mock_base_service):
        """Test control command with error."""
        mock_base_service.start.side_effect = Exception("Service error")
        response = app_with_service.post("/control", json={"command": "start"})
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Service error" in response.json()["detail"]


class TestServiceRetrieval:
    """Test service retrieval functionality."""
    
    def test_get_service_success(self, mock_base_service):
        """Test successful service retrieval."""
        app = FastAPI()
        app.state.service = mock_base_service
        service = get_service_from_app(app, BaseService)
        assert service == mock_base_service
        
    def test_get_service_wrong_type(self, mock_base_service):
        """Test service retrieval with wrong type."""
        app = FastAPI()
        app.state.service = mock_base_service
        with pytest.raises(HTTPException) as exc:
            get_service_from_app(app, ConfigurableService)
        assert_error_response(
            exc,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Service ConfigurableService not initialized"
        )
        
    def test_get_service_not_initialized(self):
        """Test service retrieval when not initialized."""
        app = FastAPI()
        with pytest.raises(HTTPException) as exc:
            get_service_from_app(app, BaseService)
        assert_error_response(
            exc,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Service BaseService not initialized"
        )
