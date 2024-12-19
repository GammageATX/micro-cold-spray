"""Unit tests for base router functionality."""

import pytest
from fastapi import FastAPI, APIRouter, status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from micro_cold_spray.core.base.services.base_service import BaseService
from micro_cold_spray.core.base.router import (
    add_health_endpoints,
    get_service_from_app,
    get_service,
    create_service_dependency
)
from micro_cold_spray.core.errors.exceptions import ConfigurationError

class TestHealthEndpoint:
    """Test health check endpoint functionality."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI application."""
        return FastAPI()

    @pytest.fixture
    def mock_service(self):
        """Create mock base service."""
        service = MagicMock(spec=BaseService)
        service.is_running = True
        service.start_time = None
        service._service_name = "test_service"
        service.version = "1.0.0"
        service.check_health = AsyncMock()
        return service

    @pytest.fixture
    def client(self, app, mock_service):
        """Create test client with mock service."""
        router = APIRouter()
        app.state.service = mock_service
        add_health_endpoints(router, mock_service)
        app.include_router(router)
        return TestClient(app)
    
    def test_health_check_success(self, client, mock_service):
        """Test successful health check."""
        mock_service.check_health.return_value = {
            "status": "ok",
            "message": "Service is healthy",
            "service_info": {
                "name": "test_service",
                "version": "1.0.0",
                "running": True,
                "uptime": "0:00:00"
            }
        }
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service_name"] == "test_service"
        assert data["version"] == "1.0.0"
        assert data["is_running"] is True
        
    def test_health_check_error(self, client, mock_service):
        """Test health check with error."""
        mock_service.check_health.side_effect = Exception("Service error")
        response = client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Service error" in response.json()["detail"]
        
    def test_health_check_degraded(self, client, mock_service):
        """Test health check with degraded status."""
        mock_service.check_health.return_value = {
            "status": "degraded",
            "message": "Performance degraded",
            "service_info": {
                "name": "test_service",
                "version": "1.0.0",
                "running": True,
                "uptime": "0:00:00"
            }
        }
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "degraded"
        assert data["message"] == "Performance degraded"
        
    def test_health_check_not_running(self, client, mock_service):
        """Test health check when service is not running."""
        mock_service.is_running = False
        response = client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Service is not running" in response.json()["detail"]

    def test_health_check_config_error(self, client, mock_service):
        """Test health check with configuration error."""
        mock_service.check_health.side_effect = ConfigurationError("Config error")
        response = client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Config error" in response.json()["detail"]

class TestServiceDependencies:
    """Test service dependency functionality."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI application."""
        return FastAPI()

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        return MagicMock(spec=BaseService)

    def test_get_service_from_app(self, app, mock_service):
        """Test getting service from app state."""
        app.state.service = mock_service
        service = get_service_from_app(app, BaseService)
        assert service == mock_service

    def test_get_service_from_app_error(self, app):
        """Test error when service not in app state."""
        with pytest.raises(Exception):
            get_service_from_app(app, BaseService)

    def test_create_service_dependency(self, app, mock_service):
        """Test service dependency creation."""
        app.state.service = mock_service
        dependency = create_service_dependency(BaseService)
        
        # Create mock request with app
        request = MagicMock()
        request.app = app
        
        service = dependency(request)
        assert service == mock_service 