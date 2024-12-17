"""Tests for config API router."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime
import yaml
import copy
import asyncio
import json

from micro_cold_spray.api.config.router import app, init_router, router, get_service
from micro_cold_spray.api.config.service import ConfigService
from micro_cold_spray.api.config.models import ConfigUpdate, ConfigValidationResult
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
    
    # Define uptime property getter
    def get_uptime(self):
        if not self.is_running or self.start_time is None:
            return None
        return (datetime.now() - self.start_time).total_seconds()
    
    # Set uptime as a property
    type(service).uptime = property(get_uptime)
    
    # Mock health check to return proper status
    async def mock_health_check():
        response = {
            "status": "stopped" if not service.is_running else "ok",
            "uptime": service.uptime,
            "memory_usage": 0,
            "service_info": {
                "name": service._service_name,
                "version": service.version,
                "running": service.is_running,
                "error": None
            }
        }
        
        if service.is_running:
            response.update({
                "services": {
                    "cache": True,
                    "file": True,
                    "schema": True,
                    "registry": True,
                    "format": True
                },
                "schema_loaded": True,
                "last_error": None,
                "last_update": None
            })
        
        return response
    
    service.check_health = mock_health_check
    
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
    mock_config_service.check_health = AsyncMock(return_value={
        "status": "error",
        "error": "Test error"
    })
    
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["service_info"]["error"] == "Test error"


def test_health_check_stopped(test_client, mock_config_service):
    """Test health check when service is stopped."""
    # Set service to stopped state
    mock_config_service.is_running = False
    mock_config_service.check_config_access = AsyncMock(return_value=False)
    mock_config_service.start_time = None  # Set start_time to None when stopped
    
    response = test_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "stopped"
    assert data["uptime"] is None
    assert "memory_usage" in data
    assert data["service_info"]["name"] == "config"
    assert data["service_info"]["version"] == "1.0.0"
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
    assert data["detail"]["error"] == "Configuration Error"
    assert data["detail"]["message"] == "Config not found"


def test_update_config_success(test_client, mock_config_service):
    """Test updating configuration successfully."""
    # Mock validation result
    mock_validation = ConfigValidationResult(valid=True, errors=[], warnings=[])
    mock_config_service.update_config = AsyncMock(return_value=mock_validation)
    
    config_data = {"key": "value"}
    response = test_client.post("/config/test", json=config_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "updated"
    
    # Verify update was called with backup enabled
    mock_config_service.update_config.assert_called_once()
    call_args = mock_config_service.update_config.call_args[0][0]
    assert isinstance(call_args, ConfigUpdate)
    assert call_args.config_type == "test"
    assert call_args.data == config_data
    assert call_args.backup is True
    assert call_args.should_validate is True


def test_update_config_validation_error(test_client, mock_config_service):
    """Test updating configuration with validation error."""
    mock_config_service.update_config = AsyncMock(
        side_effect=ConfigurationError("Invalid config", {"field": "key"})
    )
    
    config_data = {"key": "invalid"}
    response = test_client.post("/config/test", json=config_data)
    assert response.status_code == 400
    
    data = response.json()
    assert data["detail"]["error"] == "Configuration Error"
    assert data["detail"]["message"] == "Invalid config"
    assert "field" in data["detail"]["data"]


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
    assert data["detail"]["error"] == "Internal Server Error"
    assert data["detail"]["message"] == "Cache error"


@pytest.mark.asyncio
async def test_startup_event():
    """Test startup event initialization."""
    # Create a fresh app instance
    from micro_cold_spray.api.config.router import app, lifespan
    
    # Reset app state
    app.dependency_overrides = {}
    app.router.routes = []
    
    # Mock ConfigService
    mock_service = MagicMock(spec=ConfigService)
    mock_service.start = AsyncMock()
    mock_service.stop = AsyncMock()
    
    with patch('micro_cold_spray.api.config.router.ConfigService', return_value=mock_service):
        # Test lifespan context manager
        async with lifespan(app):
            # Verify service was started
            mock_service.start.assert_called_once()
            
            # Verify health endpoints were added
            assert any(route.path == "/health" for route in app.routes)
        
        # Verify service was stopped
        mock_service.stop.assert_called_once()


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
    from fastapi import HTTPException

    # Reset service to None
    import sys
    sys.modules['micro_cold_spray.api.config.router']._service = None

    with pytest.raises(HTTPException) as exc:
        get_service()
    assert exc.value.status_code == 503
    assert exc.value.detail["error"] == "Service Unavailable"
    assert "Config service not initialized" in exc.value.detail["message"]


@pytest.mark.asyncio
async def test_update_config_with_backup(test_client, tmp_path):
    """Test updating configuration with backup creation."""
    # Create a real config service with temp directory
    from micro_cold_spray.api.config.service import ConfigService
    
    # Set up test directories
    test_config_dir = tmp_path / "test_config"
    test_config_dir.mkdir()
    test_schema_dir = test_config_dir / "schemas"
    test_schema_dir.mkdir()
    test_backup_dir = test_config_dir / "backups"
    test_backup_dir.mkdir()
    
    # Create test schema for all required types
    test_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "application": {
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "object",
                        "properties": {
                            "mode": {"type": "string", "enum": ["test", "development", "production"]},
                            "version": {"type": "string"}
                        }
                    },
                    "info": {
                        "type": "object",
                        "properties": {
                            "version": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
    
    # Write schema for all required types
    for schema_type in ["application", "hardware", "process", "tags", "state", "file_format"]:
        schema_dest = test_schema_dir / f"{schema_type}.json"
        with open(schema_dest, "w") as f:
            json.dump(test_schema, f)
    
    # Create test config file
    test_config = {
        "application": {
            "environment": {
                "mode": "development",
                "version": "1.0.0"
            },
            "info": {
                "version": "1.0.0"
            }
        }
    }
    test_config_dest = test_config_dir / "application.yaml"
    with open(test_config_dest, "w") as f:
        yaml.dump(test_config, f)
    
    # Create and initialize service with test paths
    service = ConfigService()
    service._config_dir = test_config_dir
    service._schema_dir = test_schema_dir
    service._file_service._config_dir = test_config_dir
    service._file_service._backup_dir = test_backup_dir
    service._schema_service._schema_dir = test_schema_dir
    
    # Override app dependency
    app.dependency_overrides[get_service] = lambda: service
    
    # Start service
    await service.start()
    
    try:
        # Load initial config for comparison
        with open(test_config_dest) as f:
            initial_config = yaml.load(f, Loader=yaml.Loader)
        
        # Store a deep copy of initial config for backup comparison
        backup_comparison = copy.deepcopy(initial_config)
        
        # Update config with valid changes
        update_dict = {
            "config_type": "application",
            "data": {
                "application": {
                    "environment": {
                        "mode": "test"
                    },
                    "info": {
                        "version": "2.0.0"
                    }
                }
            },
            "backup": True,
            "validate": True
        }
        
        response = test_client.post("/config/application", json=update_dict)
        assert response.status_code == 200
        
        # Wait a short time for backup to be created
        await asyncio.sleep(0.1)
        
        # Verify backup was created in backup directory
        backup_files = list(test_backup_dir.glob("application_*.bak"))
        assert len(backup_files) == 1
        backup_path = backup_files[0]
        
        # Verify backup contains original data
        with open(backup_path) as f:
            backup_data = yaml.load(f, Loader=yaml.Loader)
            assert backup_data == backup_comparison
        
        # Verify config was updated
        with open(test_config_dest) as f:
            updated_data = yaml.load(f, Loader=yaml.Loader)
            assert "application" in updated_data
            assert updated_data["application"]["environment"]["mode"] == "test"
            assert updated_data["application"]["info"]["version"] == "2.0.0"
            
    finally:
        # Clean up
        await service.stop()
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_config_health(config_service):
    """Test config health endpoint."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{config_service}/health") as response:
            assert response.status == 200
            data = await response.json()
            assert data["status"] == "ok"
            assert "uptime" in data
            assert "memory_usage" in data
            assert "service_info" in data


@pytest.mark.asyncio
async def test_config_endpoints(config_service, tmp_path):
    """Test config endpoints."""
    # Create and initialize service
    from micro_cold_spray.api.config.service import ConfigService

    # Create test directories
    test_config_dir = tmp_path / "test_config"
    test_config_dir.mkdir(exist_ok=True)
    test_schema_dir = test_config_dir / "schemas"
    test_schema_dir.mkdir(exist_ok=True)

    # Create test schema
    test_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "application": {
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "object",
                        "properties": {
                            "mode": {"type": "string", "enum": ["test", "development", "production"]},
                            "version": {"type": "string"}
                        }
                    }
                }
            }
        }
    }

    # Write schema
    schema_dest = test_schema_dir / "application.json"
    with open(schema_dest, "w") as f:
        json.dump(test_schema, f)

    # Create test config file
    test_config = {
        "application": {
            "environment": {
                "mode": "development",
                "version": "1.0.0"
            }
        }
    }
    config_dest = test_config_dir / "application.yaml"
    with open(config_dest, "w") as f:
        yaml.dump(test_config, f)

    # Create and initialize service
    service = ConfigService()
    service._config_dir = test_config_dir
    service._schema_dir = test_schema_dir

    # Override app dependency
    app.dependency_overrides[get_service] = lambda: service

    try:
        # Start service
        await service.start()

        # Test endpoints
        test_client = TestClient(app)
        
        # Enable and initialize cache service
        service._cache_service.cache_enabled = True
        await service._cache_service.start()
        
        # Set cache configuration in service
        service._config = {
            "application": {
                "services": {
                    "config_manager": {
                        "cache_enabled": True,
                        "cache_timeout": 3600,
                        "validation_enabled": True
                    }
                }
            }
        }
        
        # Test get config types
        response = test_client.get("/config/types")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Test get config
        response = test_client.get("/config/application")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data

        # Test update config
        config_data = {
            "config_type": "application",
            "data": {
                "application": {
                    "environment": {
                        "mode": "test"
                    }
                }
            },
            "backup": True,
            "validate": True
        }
        response = test_client.post("/config/application", json=config_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"

        # Test clear cache
        response = test_client.post("/config/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Cache cleared"

    finally:
        # Clean up
        await service.stop()
        app.dependency_overrides.clear()
