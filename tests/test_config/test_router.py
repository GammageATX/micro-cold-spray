"""Tests for config API router."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime
from pathlib import Path
import yaml
import copy
from httpx import AsyncClient
import shutil
import asyncio

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
    
    # Reset service to None
    import sys
    sys.modules['micro_cold_spray.api.config.router']._service = None
    
    with pytest.raises(RuntimeError, match="Config service not initialized"):
        get_service()


@pytest.mark.asyncio
async def test_update_config_with_backup(test_client, tmp_path):
    """Test updating configuration with backup creation."""
    # Create a real config service with temp directory
    from micro_cold_spray.api.config.service import ConfigService
    
    # Set up test directories
    test_data_dir = Path(__file__).parent / "test_data"
    test_config_dir = tmp_path / "test_config"
    test_config_dir.mkdir()
    test_schema_dir = test_config_dir / "schemas"
    test_schema_dir.mkdir()
    test_backup_dir = test_config_dir / "backups"
    test_backup_dir.mkdir()
    
    # Copy test schema and config
    test_schema_path = test_data_dir / "schemas" / "test_config.json"
    test_config_path = test_data_dir / "test_config.yaml"
    
    # Copy test schema for all required types
    for schema_type in ["application", "hardware", "process", "tags", "state", "file_format"]:
        schema_dest = test_schema_dir / f"{schema_type}.json"
        schema_dest.write_text(test_schema_path.read_text())
    
    # Create initial test config file
    test_config_dest = test_config_dir / "application.yaml"
    shutil.copy2(test_config_path, test_config_dest)  # Copy the real config file
    
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
            initial_config = yaml.safe_load(f)
        
        # Store a deep copy of initial config for backup comparison
        backup_comparison = copy.deepcopy(initial_config)  # Keep the full structure
        
        # Update config with valid changes that match application.yaml structure
        updated_config = copy.deepcopy(initial_config)  # Start with full structure
        updated_config["application"]["environment"]["test_value"] = "updated_test"
        updated_config["application"]["info"]["version"] = "2.0.0"
        
        # Enable backup in service and file service
        service._file_service.backup_enabled = True
        service._config = {
            "application": {
                "services": {
                    "config_manager": {
                        "backup_enabled": True,
                        "backup_interval": 3600,
                        "validation_enabled": True
                    }
                }
            }
        }
        
        # Create backup directory if it doesn't exist
        test_backup_dir.mkdir(exist_ok=True)
        
        # Set backup directory in file service
        service._file_service._backup_dir = test_backup_dir
        service._file_service.backup_enabled = True
        
        # Set backup configuration in service
        service._config = {
            "application": {
                "services": {
                    "config_manager": {
                        "backup_enabled": True,
                        "backup_interval": 3600,
                        "validation_enabled": True
                    }
                }
            }
        }
        
        # Create update request with backup enabled
        update_dict = {
            "config_type": "application",
            "data": {
                "application": {
                    "environment": {
                        "test_value": "updated_test"
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
            backup_data = yaml.safe_load(f)
            assert backup_data == backup_comparison
        
        # Verify config was updated
        with open(test_config_dest) as f:
            updated_data = yaml.safe_load(f)
            assert "application" in updated_data
            assert updated_data["application"]["environment"]["test_value"] == "updated_test"
            assert updated_data["application"]["info"]["version"] == "2.0.0"
            
    finally:
        # Clean up
        await service.stop()
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_config_health(config_service):
    async with AsyncClient() as client:
        response = await client.get(f"{config_service}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_config_endpoints(config_service, tmp_path):
    """Test config endpoints."""
    # Create and initialize service
    from micro_cold_spray.api.config.service import ConfigService

    # Create test directories
    test_data_dir = Path(__file__).parent / "test_data"
    test_config_dir = tmp_path / "test_config"  # Use tmp_path instead of root directory
    test_config_dir.mkdir(exist_ok=True)
    test_schema_dir = test_config_dir / "schemas"
    test_schema_dir.mkdir(exist_ok=True)

    # Copy test schema for application
    test_schema_path = test_data_dir / "schemas" / "test_config.json"
    schema_dest = test_schema_dir / "application.json"
    schema_dest.write_text(test_schema_path.read_text())

    # Create test config file
    test_config_path = test_data_dir / "test_config.yaml"
    config_dest = test_config_dir / "application.yaml"
    config_dest.write_text(test_config_path.read_text())

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
        await service._cache_service.start()  # Properly await the start
        
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
                        "test_value": "test"
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
        # No need to manually remove test_config_dir as it's under tmp_path
