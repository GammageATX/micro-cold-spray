"""Tests for configuration service."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException, status

from micro_cold_spray.api.config.service import ConfigService
from .helpers import (
    create_config_data,
    create_test_schema,
    create_config_update
)


@pytest.fixture
def mock_services():
    """Create mock services."""
    services = {
        "cache": MagicMock(),
        "file": MagicMock(),
        "schema": MagicMock(),
        "registry": MagicMock(),
        "format": MagicMock()
    }
    
    # Setup common async methods
    for service in services.values():
        service.start = AsyncMock()
        service.stop = AsyncMock()
    
    # Setup specific async methods
    services["cache"].get_cached_config = AsyncMock()
    services["cache"].cache_config = AsyncMock()
    services["cache"].invalidate = AsyncMock()
    services["cache"].clear = AsyncMock()
    
    services["file"].load_config = AsyncMock()
    services["file"].save_config = AsyncMock()
    services["file"].create_backup = AsyncMock()
    
    services["registry"].validate_tag = AsyncMock()
    services["registry"].update_tag_references = AsyncMock()
    services["registry"].validate_references = AsyncMock()
    
    services["schema"].validate_config = AsyncMock()
    
    return services


@pytest.fixture
def test_schema():
    """Create test schema."""
    return {
        "type": "object",
        "properties": {
            "key": {"type": "string"}
        }
    }


@pytest.fixture
def test_config():
    """Create test config data."""
    return create_config_data(
        name="test",
        data={"key": "value"}
    )


@pytest.fixture
def config_service(mock_services, tmp_path, test_schema):
    """Create config service with mock dependencies."""
    with patch('micro_cold_spray.api.config.service.ConfigCacheService',
               return_value=mock_services["cache"]), \
         patch('micro_cold_spray.api.config.service.ConfigFileService',
               return_value=mock_services["file"]), \
         patch('micro_cold_spray.api.config.service.SchemaService',
               return_value=mock_services["schema"]), \
         patch('micro_cold_spray.api.config.service.RegistryService',
               return_value=mock_services["registry"]), \
         patch('micro_cold_spray.api.config.service.FormatService',
               return_value=mock_services["format"]):
        
        service = ConfigService()
        service._config_dir = tmp_path / "config"
        service._schema_dir = service._config_dir / "schemas"
        
        # Create test directories
        service._config_dir.mkdir(exist_ok=True)
        service._schema_dir.mkdir(exist_ok=True)
        
        # Create test schema files
        create_test_schema(service._schema_dir, "test", test_schema)
        create_test_schema(service._schema_dir, "application", {
            "type": "object",
            "properties": {
                "tag": {"type": "string"}
            }
        })
        
        return service


@pytest.mark.asyncio
async def test_service_start(config_service, mock_services, test_schema):
    """Test service startup."""
    # Mock schema loading
    mock_services["schema"].get_schema = MagicMock(return_value=test_schema)
    
    # Start service
    await config_service.start()
    
    # Verify all services were started
    for service in mock_services.values():
        service.start.assert_called_once()
    
    # Verify schema registry was loaded
    assert config_service._schema_registry is not None


@pytest.mark.asyncio
async def test_service_start_error(config_service, mock_services):
    """Test service startup with error."""
    # Make schema service fail
    mock_services["schema"].start.side_effect = Exception("Schema error")
    
    # Verify startup fails
    with pytest.raises(Exception, match="Schema error"):
        await config_service.start()


@pytest.mark.asyncio
async def test_service_stop(config_service, mock_services, test_schema):
    """Test service shutdown."""
    # Start service first
    mock_services["schema"].get_schema = MagicMock(return_value=test_schema)
    await config_service.start()
    
    # Stop service
    await config_service.stop()
    
    # Verify all services were stopped
    for service in mock_services.values():
        service.stop.assert_called_once()


@pytest.mark.asyncio
async def test_service_stop_error(config_service, mock_services, test_schema):
    """Test service shutdown with error."""
    # Start service first
    mock_services["schema"].get_schema = MagicMock(return_value=test_schema)
    await config_service.start()
    
    # Make cache service fail during stop
    mock_services["cache"].stop.side_effect = Exception("Cache error")
    
    # Verify shutdown fails
    with pytest.raises(Exception, match="Cache error"):
        await config_service.stop()


@pytest.mark.asyncio
async def test_get_config(config_service, mock_services, test_schema, test_config):
    """Test getting configuration."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value=test_schema)
    await config_service.start()
    
    # Mock cache miss and file load
    mock_services["cache"].get_cached_config.return_value = None
    mock_services["file"].load_config.return_value = test_config
    
    # Get config
    config = await config_service.get_config("test")
    
    # Verify cache was checked and file was loaded
    mock_services["cache"].get_cached_config.assert_called_once_with("test")
    mock_services["file"].load_config.assert_called_once_with("test")
    
    # Verify config was cached
    mock_services["cache"].cache_config.assert_called_once_with("test", test_config)
    
    # Verify returned config
    assert config == test_config


@pytest.mark.asyncio
async def test_get_config_cached(config_service, mock_services, test_schema, test_config):
    """Test getting cached configuration."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value=test_schema)
    await config_service.start()
    
    # Mock cache hit
    mock_services["cache"].get_cached_config.return_value = test_config
    
    # Get config
    config = await config_service.get_config("test")
    
    # Verify cache was checked but file was not loaded
    mock_services["cache"].get_cached_config.assert_called_once_with("test")
    mock_services["file"].load_config.assert_not_called()
    
    # Verify returned config
    assert config == test_config


@pytest.mark.asyncio
async def test_get_config_error(config_service, mock_services, test_schema):
    """Test getting configuration with error."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value=test_schema)
    await config_service.start()
    
    # Mock cache miss and file error
    mock_services["cache"].get_cached_config.return_value = None
    mock_services["file"].load_config.side_effect = Exception("File error")
    
    # Verify error is wrapped in HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await config_service.get_config("test")
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "File error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_config(config_service, mock_services, test_schema, test_config):
    """Test updating configuration."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value=test_schema)
    await config_service.start()
    
    # Mock schema registry after service start
    config_service._schema_registry = MagicMock()
    config_service._schema_registry.model_fields = {"test": test_schema}
    config_service._schema_registry.test = test_schema
    
    # Mock validation success
    mock_services["schema"].validate_config = AsyncMock(return_value=[])  # Empty list means no errors
    
    # Create update request
    update = create_config_update(
        config_type="test",
        data={"key": "new_value"}
    )
    
    # Update config
    result = await config_service.update_config(update)
    assert result.valid is True
    assert len(result.errors) == 0
    
    # Verify backup was created and config was saved
    mock_services["file"].create_backup.assert_called_once_with("test")
    mock_services["file"].save_config.assert_called_once()
    mock_services["cache"].cache_config.assert_called_once()
