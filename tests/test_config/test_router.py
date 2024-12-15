"""Tests for config API router."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from micro_cold_spray.api.config.router import app, init_router, router
from micro_cold_spray.api.config.service import ConfigService
from micro_cold_spray.api.base.exceptions import ConfigurationError
from micro_cold_spray.api.base.router import add_health_endpoints


@pytest.fixture
def mock_config_service():
    """Create a mock config service."""
    service = MagicMock(spec=ConfigService)
    service.is_running = True
    service.start_time = datetime.now()
    service._service_name = "config"
    service.version = "1.0.0"
    return service


@pytest.fixture
def test_client(mock_config_service):
    """Create a test client with mock service."""
    # Reset the app state
    app.dependency_overrides = {}
    app.router.routes = []
    
    # Initialize router and add health endpoints
    init_router(mock_config_service)
    add_health_endpoints(app, mock_config_service)
    
    # Include router in app
    app.include_router(router)
    
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_service():
    """Reset the service state before each test."""
    from micro_cold_spray.api.config.router import _service
    import sys
    
    # Store original service
    original_service = _service
    
    # Reset service
    sys.modules['micro_cold_spray.api.config.router']._service = None
    
    yield
    
    # Restore original service
    sys.modules['micro_cold_spray.api.config.router']._service = original_service


def test_get_config_types(test_client):
    """Test getting available config types."""
    response = test_client.get("/config/types")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 6  # application, hardware, file_format, process, state, tags
    
    # Verify each config type has required fields
    for config_type in data:
        assert "id" in config_type
        assert "name" in config_type


def test_health_check_success(test_client, mock_config_service):
    """Test successful health check."""
    # Mock check_config_access to return True
    mock_config_service.check_config_access = AsyncMock(return_value=True)
    mock_config_service.is_running = True
    
    response = test_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime" in data
    assert "memory_usage" in data
    assert data["service_info"]["name"] == "config"
    assert data["service_info"]["version"] == "1.0.0"
    assert data["service_info"]["running"] is True


def test_health_check_error(test_client, mock_config_service):
    """Test health check with error."""
    # Mock check_health to return error status
    mock_config_service.check_health = AsyncMock(return_value={
        "status": "error",
        "error": "Test error"
    })
    mock_config_service.is_running = True
    
    response = test_client.get("/health")
    assert response.status_code == 200  # Still returns 200 but with error status
    
    data = response.json()
    assert data["status"] == "error"
    assert "error" in data["service_info"]
    assert data["service_info"]["name"] == "config"
    assert data["service_info"]["running"] is True


def test_health_check_stopped(test_client, mock_config_service):
    """Test health check when service is stopped."""
    mock_config_service.check_config_access = AsyncMock(return_value=True)
    mock_config_service.is_running = False
    
    response = test_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "stopped"
    assert data["service_info"]["name"] == "config"
    assert data["service_info"]["running"] is False


def test_get_config_success(test_client, mock_config_service):
    """Test getting configuration successfully."""
    mock_config = {
        "metadata": {
            "config_type": "test",
            "last_modified": datetime.now().isoformat(),
            "version": "1.0.0"
        },
        "data": {"key": "value"}
    }
    mock_config_service.get_config = AsyncMock(return_value=mock_config)
    
    response = test_client.get("/config/test")
    assert response.status_code == 200
    
    data = response.json()
    assert "config" in data
    assert data["config"]["data"]["key"] == "value"


def test_get_config_not_found(test_client, mock_config_service):
    """Test getting non-existent configuration."""
    mock_config_service.get_config = AsyncMock(
        side_effect=ConfigurationError("Config not found")
    )
    
    response = test_client.get("/config/nonexistent")
    assert response.status_code == 400
    
    data = response.json()
    assert "error" in data["detail"]


def test_update_config_success(test_client, mock_config_service):
    """Test updating configuration successfully."""
    mock_config_service.update_config = AsyncMock(return_value=None)
    
    config_data = {"key": "value"}
    response = test_client.post("/config/test", json=config_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "updated"


def test_update_config_validation_error(test_client, mock_config_service):
    """Test updating configuration with validation error."""
    mock_config_service.update_config = AsyncMock(
        side_effect=ConfigurationError("Invalid config", {"field": "key"})
    )
    
    config_data = {"key": "invalid"}
    response = test_client.post("/config/test", json=config_data)
    assert response.status_code == 400
    
    data = response.json()
    assert "error" in data["detail"]
    assert "context" in data["detail"]


def test_clear_cache_success(test_client, mock_config_service):
    """Test clearing cache successfully."""
    mock_config_service.clear_cache = AsyncMock(return_value=None)
    
    response = test_client.post("/config/cache/clear")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "Cache cleared"


def test_clear_cache_error(test_client, mock_config_service):
    """Test clearing cache with error."""
    mock_config_service.clear_cache = AsyncMock(
        side_effect=Exception("Cache error")
    )
    
    response = test_client.post("/config/cache/clear")
    assert response.status_code == 500
    
    data = response.json()
    assert "error" in data["detail"]


@pytest.mark.asyncio
async def test_startup_event():
    """Test startup event initialization."""
    # Create a fresh app instance
    from micro_cold_spray.api.config.router import app, startup_event
    
    # Reset app state
    app.dependency_overrides = {}
    app.router.routes = []
    
    # Mock ConfigService
    mock_service = MagicMock(spec=ConfigService)
    mock_service.start = AsyncMock()
    
    with patch('micro_cold_spray.api.config.router.ConfigService', return_value=mock_service):
        await startup_event()
        
        # Verify service was started
        mock_service.start.assert_called_once()
        
        # Verify health endpoints were added
        assert any(route.path == "/health" for route in app.routes)


def test_init_router_with_service():
    """Test router initialization with service instance."""
    # Create a fresh app instance
    from micro_cold_spray.api.config.router import app
    
    # Reset app state
    app.dependency_overrides = {}
    app.router.routes = []
    
    # Create mock service
    mock_service = MagicMock(spec=ConfigService)
    
    # Initialize router
    init_router(mock_service)
    add_health_endpoints(app, mock_service)
    app.include_router(router)
    
    # Verify routes were added
    route_paths = [route.path for route in app.routes]
    assert "/config/types" in route_paths
    assert "/config/{config_type}" in route_paths
    assert "/config/cache/clear" in route_paths
    assert "/health" in route_paths


def test_get_service_not_initialized():
    """Test getting service when not initialized."""
    from micro_cold_spray.api.config.router import get_service
    
    # Reset service to None
    import sys
    sys.modules['micro_cold_spray.api.config.router']._service = None
    
    with pytest.raises(RuntimeError, match="Config service not initialized"):
        get_service()
