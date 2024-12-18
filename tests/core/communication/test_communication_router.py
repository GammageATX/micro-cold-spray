"""Tests for communication router."""

import sys
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# Mock asyncssh before importing router
sys.modules['asyncssh'] = MagicMock()

from micro_cold_spray.api.communication.router import (  # noqa: E402
    router,
    get_service,
    init_router,
    app,
    lifespan  # Import lifespan directly
)
from micro_cold_spray.api.communication.service import CommunicationService  # noqa: E402
from micro_cold_spray.api.base.exceptions import ServiceError  # noqa: E402
from micro_cold_spray.api.base.errors import ErrorCode, format_error  # noqa: E402
from micro_cold_spray.api.config.models import ConfigData, ConfigMetadata  # noqa: E402


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    service = AsyncMock()
    type(service).is_initialized = PropertyMock(return_value=True)
    type(service).is_running = PropertyMock(side_effect=[False, False])  # First call returns False, second call also returns False
    
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
    type(service).is_initialized = PropertyMock(return_value=True)
    type(service).is_running = PropertyMock(return_value=True)
    type(service)._service_name = PropertyMock(return_value="CommunicationService")
    type(service).version = PropertyMock(return_value="1.0.0")
    type(service).uptime = PropertyMock(return_value="0:00:00")
    
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
    app.include_router(router, prefix="/api/v1")
    init_router(mock_communication_service)
    app.state.service = mock_communication_service  # Store service in app state
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestCommunicationRouter:
    """Test communication router functionality."""

    def test_router_initialization(self):
        """Test router initialization."""
        assert router.prefix == "/communication"
        assert "communication" in router.tags

    def test_get_service_success(self, mock_communication_service):
        """Test successful service dependency injection."""
        init_router(mock_communication_service)
        service = get_service()
        assert service == mock_communication_service
        assert service.is_initialized
        assert service.is_running

    def test_get_service_not_initialized(self):
        """Test service dependency when not initialized."""
        init_router(None)
        with pytest.raises(HTTPException) as exc_info:
            get_service()
        assert exc_info.value.status_code == ErrorCode.SERVICE_UNAVAILABLE.get_status_code()
        assert exc_info.value.detail == format_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            "CommunicationService not initialized"
        )["detail"]

    @pytest.mark.asyncio
    async def test_startup_shutdown(self, mock_config_service, mock_communication_service):
        """Test startup and shutdown through lifespan."""
        type(mock_config_service).is_running = PropertyMock(return_value=True)
        with patch('micro_cold_spray.api.config.singleton.get_config_service', return_value=mock_config_service):
            async with lifespan(app):
                assert app.state.service is not None
                assert app.state.service.is_running
            assert app.state.service is None

    @pytest.mark.asyncio
    async def test_startup_failure(self, mock_config_service):
        """Test startup failure handling."""
        # Mock the start method to raise an error
        error_message = "Test error"
        mock_config_service.start = AsyncMock(side_effect=ServiceError(error_message))
        type(mock_config_service).is_running = PropertyMock(return_value=False)
        
        with patch('micro_cold_spray.api.config.singleton.get_config_service', return_value=mock_config_service):
            with pytest.raises(ServiceError) as exc_info:  # Expect the exact ServiceError
                async with lifespan(app):
                    pass  # Should not reach this point
            
            # Verify the error message and that start was called
            assert mock_config_service.start.called
            assert str(exc_info.value) == "ConfigService failed to start"

    def test_health_check_success(self, client, mock_communication_service):
        """Test successful health check."""
        response = client.get("/api/v1/communication/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service_info"]["name"] == "CommunicationService"
        assert data["service_info"]["version"] == "1.0.0"
        assert data["service_info"]["running"] is True

    def test_health_check_service_error(self, client, mock_communication_service, test_app):
        """Test health check with service error."""
        mock_communication_service.check_health = AsyncMock(side_effect=ServiceError("Test error"))
        test_app.state.service = mock_communication_service  # Update service in app state
        response = client.get("/api/v1/communication/health")
        assert response.status_code == ErrorCode.HEALTH_CHECK_ERROR.get_status_code()
        assert response.json()["detail"] == format_error(
            ErrorCode.HEALTH_CHECK_ERROR,
            "Test error"
        )["detail"]

    def test_health_check_internal_error(self, client, mock_communication_service, test_app):
        """Test health check with internal error."""
        mock_communication_service.check_health = AsyncMock(side_effect=Exception("Test error"))
        test_app.state.service = mock_communication_service  # Update service in app state
        response = client.get("/api/v1/communication/health")
        assert response.status_code == ErrorCode.INTERNAL_ERROR.get_status_code()
        assert response.json()["detail"] == format_error(
            ErrorCode.INTERNAL_ERROR,
            "Test error"
        )["detail"]

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
        assert response.json()["detail"] == format_error(
            ErrorCode.INVALID_ACTION,
            "Invalid action: invalid",
            {"valid_actions": ["start", "stop", "restart"]}
        )["detail"]

    def test_control_service_error(self, client, mock_communication_service):
        """Test service control with service error."""
        mock_communication_service.stop = AsyncMock(side_effect=ServiceError("Test error"))
        response = client.post("/api/v1/communication/control?action=stop")
        assert response.status_code == ErrorCode.COMMUNICATION_ERROR.get_status_code()
        assert response.json()["detail"] == format_error(
            ErrorCode.COMMUNICATION_ERROR,
            "Test error"
        )["detail"]
