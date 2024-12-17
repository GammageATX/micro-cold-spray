"""Tests for communication router."""

import sys
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.testclient import TestClient

# Mock asyncssh before importing router
sys.modules['asyncssh'] = MagicMock()

from micro_cold_spray.api.communication.router import (  # noqa: E402
    router,
    get_communication_service,
    init_router,
    startup,
    shutdown
)
from micro_cold_spray.api.communication.service import CommunicationService  # noqa: E402
from micro_cold_spray.api.base.exceptions import ServiceError  # noqa: E402
from micro_cold_spray.api.base.errors import ErrorCode, format_error  # noqa: E402
from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata  # noqa: E402


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    service = AsyncMock()
    service.is_initialized = True
    service.is_running = True
    
    # Mock get_config to return proper config data
    async def mock_get_config(config_type: str):
        return ConfigData(
            metadata=ConfigMetadata(
                config_type=config_type,
                last_modified=datetime.now(),
                version="1.0.0"
            ),
            data={
                "network": {
                    "plc": {
                        "host": "localhost",
                        "port": 502
                    }
                }
            }
        )
    service.get_config.side_effect = mock_get_config
    return service


@pytest.fixture
def mock_communication_service():
    """Create mock communication service."""
    service = AsyncMock(spec=CommunicationService)
    service.is_initialized = True
    service.is_running = True
    service._service_name = "CommunicationService"
    service.version = "1.0.0"
    service.uptime = "0:00:00"
    
    # Mock health check method
    async def mock_check_health():
        return {
            "status": "healthy",
            "service_info": {
                "name": service._service_name,
                "version": service.version,
                "uptime": str(service.uptime),
                "running": service.is_running
            }
        }
    service.check_health = AsyncMock(side_effect=mock_check_health)
    
    return service


@pytest.fixture
def test_app(mock_communication_service):
    """Create test FastAPI app with communication router."""
    app = FastAPI()
    
    # Initialize router with mock service
    init_router(mock_communication_service)
    
    # Mount router to app
    app.include_router(router, prefix="/api/v1/communication")
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestCommunicationRouter:
    """Test communication router functionality."""

    def test_router_initialization(self):
        """Test router initialization."""
        assert isinstance(router, APIRouter)
        assert "communication" in router.tags

    def test_get_communication_service_success(self, mock_communication_service):
        """Test successful service dependency injection."""
        init_router(mock_communication_service)
        service = get_communication_service()
        assert service == mock_communication_service
        assert service.is_initialized
        assert service.is_running

    def test_get_communication_service_not_initialized(self):
        """Test service dependency when not initialized."""
        init_router(None)
        with pytest.raises(HTTPException) as exc_info:
            get_communication_service()
        assert exc_info.value.status_code == ErrorCode.SERVICE_UNAVAILABLE.get_status_code()
        error_detail = format_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            "Communication service not initialized"
        )["detail"]
        assert exc_info.value.detail == error_detail

    @pytest.mark.asyncio
    async def test_startup(self, mock_config_service):
        """Test startup function."""
        with patch('micro_cold_spray.api.communication.router.get_config_service', return_value=mock_config_service):
            await startup()
            mock_config_service.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_failure(self, mock_config_service):
        """Test startup failure handling."""
        mock_config_service.start.side_effect = Exception("Test error")
        with (
            patch('micro_cold_spray.api.communication.router.get_config_service', return_value=mock_config_service),
            pytest.raises(Exception, match="Test error")
        ):
            await startup()

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_communication_service):
        """Test shutdown function."""
        init_router(mock_communication_service)
        await shutdown()
        mock_communication_service.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_failure(self, mock_communication_service):
        """Test shutdown failure handling."""
        init_router(mock_communication_service)
        mock_communication_service.stop.side_effect = Exception("Test error")
        await shutdown()  # Should not raise exception
        mock_communication_service.stop.assert_called_once()

    def test_health_check_success(self, client, mock_communication_service):
        """Test successful health check."""
        response = client.get("/api/v1/communication/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service_info"]["name"] == "CommunicationService"
        assert data["service_info"]["version"] == "1.0.0"
        assert data["service_info"]["running"] is True

    def test_health_check_service_error(self, client, mock_communication_service):
        """Test health check with service error."""
        mock_communication_service.check_health.side_effect = ServiceError("Test error")
        response = client.get("/api/v1/communication/health")
        assert response.status_code == ErrorCode.HEALTH_CHECK_ERROR.get_status_code()
        error_detail = format_error(ErrorCode.HEALTH_CHECK_ERROR, "Test error")["detail"]
        assert response.json()["detail"] == error_detail

    def test_health_check_internal_error(self, client, mock_communication_service):
        """Test health check with internal error."""
        mock_communication_service.check_health.side_effect = Exception("Test error")
        response = client.get("/api/v1/communication/health")
        assert response.status_code == ErrorCode.INTERNAL_ERROR.get_status_code()
        error_detail = format_error(ErrorCode.INTERNAL_ERROR, "Test error")["detail"]
        assert response.json()["detail"] == error_detail

    @pytest.mark.parametrize("action", ["start", "stop", "restart"])
    def test_control_service_success(self, client, mock_communication_service, action):
        """Test successful service control."""
        response = client.post(f"/api/v1/communication/control?action={action}")
        assert response.status_code == 200
        assert response.json() == {"status": "stopped" if action == "stop" else action + "ed"}
        
        if action == "stop":
            mock_communication_service.stop.assert_called_once()
            mock_communication_service.start.assert_not_called()
        elif action == "start":
            mock_communication_service.start.assert_called_once()
            mock_communication_service.stop.assert_not_called()
        elif action == "restart":
            mock_communication_service.stop.assert_called_once()
            mock_communication_service.start.assert_called_once()

    def test_control_service_invalid_action(self, client):
        """Test service control with invalid action."""
        response = client.post("/api/v1/communication/control?action=invalid")
        assert response.status_code == ErrorCode.INVALID_ACTION.get_status_code()
        error_detail = format_error(
            ErrorCode.INVALID_ACTION,
            "Invalid action: invalid",
            {"valid_actions": ["start", "stop", "restart"]}
        )["detail"]
        assert response.json()["detail"] == error_detail

    def test_control_service_error(self, client, mock_communication_service):
        """Test service control with service error."""
        mock_communication_service.stop.side_effect = ServiceError("Test error")
        response = client.post("/api/v1/communication/control?action=stop")
        assert response.status_code == ErrorCode.SERVICE_UNAVAILABLE.get_status_code()
        error_detail = format_error(ErrorCode.SERVICE_UNAVAILABLE, "Test error")["detail"]
        assert response.json()["detail"] == error_detail
