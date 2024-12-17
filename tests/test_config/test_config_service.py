"""Tests for config service."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from unittest import mock

from micro_cold_spray.api.config.service import ConfigService
from micro_cold_spray.api.base.exceptions import ConfigurationError
from micro_cold_spray.api.config.models import (
    ConfigData,
    ConfigMetadata,
    ConfigUpdate,
    TagRemapRequest,
    ConfigValidationResult
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
def config_service(mock_services, tmp_path):
    """Create config service with mock dependencies."""
    with patch('micro_cold_spray.api.config.service.ConfigCacheService', return_value=mock_services["cache"]), \
         patch('micro_cold_spray.api.config.service.ConfigFileService', return_value=mock_services["file"]), \
         patch('micro_cold_spray.api.config.service.SchemaService', return_value=mock_services["schema"]), \
         patch('micro_cold_spray.api.config.service.RegistryService', return_value=mock_services["registry"]), \
         patch('micro_cold_spray.api.config.service.FormatService', return_value=mock_services["format"]):
        
        service = ConfigService()
        service._config_dir = tmp_path / "config"
        service._schema_dir = service._config_dir / "schemas"
        
        # Initialize schema registry with test schemas
        service._schema_registry = MagicMock()
        service._schema_registry.__fields__ = {
            "test": MagicMock(),
            "application": MagicMock()
        }
        service._schema_registry.test = {
            "type": "object",
            "properties": {
                "key": {"type": "string"}
            }
        }
        service._schema_registry.application = {
            "type": "object",
            "properties": {
                "tag": {"type": "string"}
            }
        }
        
        return service


@pytest.mark.asyncio
async def test_service_start(config_service, mock_services):
    """Test service startup."""
    # Mock schema loading
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    
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
async def test_service_stop(config_service, mock_services):
    """Test service shutdown."""
    # Start service first
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    await config_service.start()
    
    # Stop service
    await config_service.stop()
    
    # Verify all services were stopped
    for service in mock_services.values():
        service.stop.assert_called_once()


@pytest.mark.asyncio
async def test_service_stop_error(config_service, mock_services):
    """Test service shutdown with error."""
    # Start service first
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    await config_service.start()
    
    # Make cache service fail during stop
    mock_services["cache"].stop.side_effect = Exception("Cache error")
    
    # Verify shutdown fails
    with pytest.raises(Exception, match="Cache error"):
        await config_service.stop()


@pytest.mark.asyncio
async def test_get_config(config_service, mock_services):
    """Test getting configuration."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    await config_service.start()
    
    # Mock cache miss and file load
    mock_services["cache"].get_cached_config.return_value = None
    mock_config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"key": "value"}
    )
    mock_services["file"].load_config.return_value = mock_config
    
    # Get config
    config = await config_service.get_config("test")
    
    # Verify cache was checked and file was loaded
    mock_services["cache"].get_cached_config.assert_called_once_with("test")
    mock_services["file"].load_config.assert_called_once_with("test")
    
    # Verify config was cached
    mock_services["cache"].cache_config.assert_called_once_with("test", mock_config)
    
    # Verify returned config
    assert config == mock_config


@pytest.mark.asyncio
async def test_get_config_cached(config_service, mock_services):
    """Test getting cached configuration."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    await config_service.start()
    
    # Mock cache hit
    mock_config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"key": "value"}
    )
    mock_services["cache"].get_cached_config.return_value = mock_config
    
    # Get config
    config = await config_service.get_config("test")
    
    # Verify cache was checked but file was not loaded
    mock_services["cache"].get_cached_config.assert_called_once_with("test")
    mock_services["file"].load_config.assert_not_called()
    
    # Verify returned config
    assert config == mock_config


@pytest.mark.asyncio
async def test_get_config_error(config_service, mock_services):
    """Test getting configuration with error."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    await config_service.start()
    
    # Mock cache miss and file error
    mock_services["cache"].get_cached_config.return_value = None
    mock_services["file"].load_config.side_effect = Exception("File error")
    
    # Verify error is wrapped
    with pytest.raises(ConfigurationError, match="Failed to get config test"):
        await config_service.get_config("test")


@pytest.mark.asyncio
async def test_update_config(config_service, mock_services):
    """Test updating configuration."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    await config_service.start()
    
    # Mock successful validation
    mock_services["schema"].validate_config.return_value = []
    mock_services["registry"].validate_references.return_value = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Create update request
    update = ConfigUpdate(
        config_type="test",
        data={"key": "value"},
        backup=True,
        should_validate=True
    )
    
    # Mock validation result
    mock_validation = ConfigValidationResult(valid=True, errors=[], warnings=[])
    config_service.validate_config = AsyncMock(return_value=mock_validation)
    
    # Mock cache service
    config_service._cache_service = mock_services["cache"]
    
    # Update config
    result = await config_service.update_config(update)
    
    # Verify validation was successful
    assert result.valid
    
    # Verify file was updated
    mock_services["file"].save_config.assert_called_once()
    
    # Verify cache was updated
    assert mock_services["cache"].cache_config.call_count == 1
    call_args = mock_services["cache"].cache_config.call_args
    assert call_args[0][0] == "test"  # First argument is config_type
    assert isinstance(call_args[0][1], ConfigData)  # Second argument is ConfigData
    assert call_args[0][1].metadata.config_type == "test"
    assert call_args[0][1].data == {"key": "value"}


@pytest.mark.asyncio
async def test_update_config_validation_error(config_service, mock_services):
    """Test updating configuration with validation error."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    await config_service.start()
    
    # Mock validation error
    mock_services["schema"].validate_config.return_value = ["Invalid field"]
    
    # Create update request
    update = ConfigUpdate(
        config_type="test",
        data={"key": "value"},
        backup=True,
        should_validate=True
    )
    
    # Mock validation result
    mock_validation = ConfigValidationResult(valid=False, errors=["Invalid field"], warnings=[])
    config_service.validate_config = AsyncMock(return_value=mock_validation)
    
    # Update config
    result = await config_service.update_config(update)
    
    # Verify validation failed
    assert not result.valid
    assert "Invalid field" in result.errors
    
    # Verify file was not updated
    mock_services["file"].save_config.assert_not_called()


@pytest.mark.asyncio
async def test_clear_cache(config_service, mock_services):
    """Test clearing configuration cache."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    await config_service.start()
    
    # Mock cache service
    config_service._cache_service = mock_services["cache"]
    
    # Clear cache
    await config_service._cache_service.clear()
    
    # Verify cache was cleared
    mock_services["cache"].clear.assert_called_once()


@pytest.mark.asyncio
async def test_remap_tag(config_service, mock_services):
    """Test remapping tag references."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    await config_service.start()
    
    # Mock successful validation and update
    mock_services["registry"].validate_tag.return_value = True
    mock_services["registry"].update_tag_references.return_value = True
    
    # Mock config data
    mock_config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="1.0.0"
        ),
        data={"tag": "old_tag"}
    )
    mock_services["cache"].get_cached_config.return_value = mock_config
    
    # Mock validation result
    mock_validation = ConfigValidationResult(valid=True, errors=[], warnings=[])
    config_service.validate_config = AsyncMock(return_value=mock_validation)
    
    # Create remap request
    request = TagRemapRequest(
        old_tag="old_tag",
        new_tag="new_tag",
        should_validate=True
    )
    
    # Remap tag
    await config_service.remap_tag(request)
    
    # Verify tag was validated
    mock_services["registry"].validate_tag.assert_called_once_with("new_tag")
    
    # Verify references were updated
    mock_services["registry"].update_tag_references.assert_called()
    
    # Verify config was updated
    mock_services["file"].save_config.assert_called()


@pytest.mark.asyncio
async def test_remap_tag_validation_error(config_service, mock_services):
    """Test remapping tag with validation error."""
    # Start service
    mock_services["schema"].get_schema = MagicMock(return_value={
        "type": "object",
        "properties": {}
    })
    await config_service.start()
    
    # Mock validation error
    mock_services["registry"].validate_tag.return_value = False
    
    # Mock registry service
    config_service._registry_service = mock_services["registry"]
    
    # Create remap request
    request = TagRemapRequest(
        old_tag="old_tag",
        new_tag="invalid_tag",
        should_validate=True
    )
    
    # Verify validation error is raised
    with pytest.raises(ConfigurationError) as exc_info:
        await config_service.remap_tag(request)
    
    # Verify error message
    error_message = str(exc_info.value)
    assert error_message == "Invalid tag: invalid_tag"
    
    # Verify references were not updated
    mock_services["registry"].update_tag_references.assert_not_called()
    mock_services["file"].save_config.assert_not_called()


@pytest.mark.asyncio
async def test_validate_config_schema_registry_not_initialized():
    """Test validation when schema registry is not initialized."""
    service = ConfigService()
    await service.start()
    service._schema_registry = None  # Force schema registry to be None
    
    with pytest.raises(ConfigurationError) as exc_info:
        await service.validate_config("application", {})
    assert "Schema registry not initialized" in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_config_unknown_type():
    """Test validation with unknown config type."""
    service = ConfigService()
    await service.start()
    
    with pytest.raises(ConfigurationError) as exc_info:
        await service.validate_config("nonexistent", {})
    assert "Unknown config type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_config_with_backup(tmp_path):
    """Test config update with backup creation."""
    # Create a temporary config directory
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    service = ConfigService()
    service._config_dir = config_dir  # Use temporary directory
    service._file_service._config_dir = config_dir  # Set config dir for file service
    await service.start()
    
    # Create initial config file
    config_data = ConfigData(
        metadata=ConfigMetadata(
            config_type="application",
            last_modified=datetime.now()
        ),
        data={"environment": "test", "log_level": "INFO"}
    )
    await service._file_service.save_config("application", config_data.data)
    
    # Use valid application config data for update
    update = ConfigUpdate(
        config_type="application",
        data={"environment": "prod", "log_level": "DEBUG"},  # Different data to verify backup
        backup=True,
        validate=True
    )
    
    # Mock validation to succeed
    async def mock_validate(*args):
        return ConfigValidationResult(valid=True, errors=[], warnings=[])
    
    with mock.patch.object(service, 'validate_config', side_effect=mock_validate):
        result = await service.update_config(update)
        assert result.valid
        
        # Verify backup was created - check backup directory for any file matching the pattern
        backup_files = list(service._file_service._backup_dir.glob("application_*.bak"))
        assert len(backup_files) > 0, "No backup file was created"
        
        # Verify original file still exists with new data
        config_path = config_dir / "application.yaml"
        assert config_path.exists()


@pytest.mark.asyncio
async def test_update_config_validation_failure():
    """Test config update with validation failure."""
    service = ConfigService()
    await service.start()
    
    # Mock validation to fail
    async def mock_validate(*args):
        return ConfigValidationResult(
            valid=False,
            errors=["Invalid config"],
            warnings=[]
        )
    
    with mock.patch.object(service, 'validate_config', side_effect=mock_validate):
        update = ConfigUpdate(
            config_type="application",
            data={"invalid": "data"},
            validate=True
        )
        
        result = await service.update_config(update)
        assert not result.valid
        assert "Invalid config" in result.errors


@pytest.mark.asyncio
async def test_remap_tag_validation_success():
    """Test successful tag remapping with validation."""
    service = ConfigService()
    await service.start()
    
    # Setup test data
    old_tag = "old_tag"
    new_tag = "new_tag"
    
    # Mock registry service validation
    async def mock_validate_tag(*args):
        return True
    
    # Mock get_config to return proper ConfigData
    async def mock_get_config(*args):
        return ConfigData(
            metadata=ConfigMetadata(
                config_type="test",
                last_modified=datetime.now()
            ),
            data={}
        )
    
    with mock.patch.object(service._registry_service, 'validate_tag', side_effect=mock_validate_tag), \
         mock.patch.object(service, 'get_config', side_effect=mock_get_config):
        request = TagRemapRequest(
            old_tag=old_tag,
            new_tag=new_tag,
            validate=True
        )
        
        await service.remap_tag(request)
        # Success if no exception raised


@pytest.mark.asyncio
async def test_remap_tag_validation_failure():
    """Test tag remapping with validation failure."""
    service = ConfigService()
    await service.start()
    
    # Mock registry service validation to fail
    async def mock_validate_tag(*args):
        return False
    
    with mock.patch.object(service._registry_service, 'validate_tag', side_effect=mock_validate_tag):
        request = TagRemapRequest(
            old_tag="old_tag",
            new_tag="invalid_tag",
            validate=True
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            await service.remap_tag(request)
        assert "Invalid tag: invalid_tag" in str(exc_info.value)


@pytest.mark.asyncio
async def test_remap_tag_update_references():
    """Test tag remapping updates references in configs."""
    service = ConfigService()
    await service.start()
    
    # Mock registry service with tag registry
    service._registry_service._tag_registry = {"new_tag"}
    
    # Mock update_tag_references to indicate changes
    async def mock_update_refs(*args):
        return True
    
    # Mock get_config to return proper ConfigData
    async def mock_get_config(*args):
        return ConfigData(
            metadata=ConfigMetadata(
                config_type="test",
                last_modified=datetime.now()
            ),
            data={}
        )
    
    with mock.patch.object(service._registry_service, 'update_tag_references', side_effect=mock_update_refs), \
         mock.patch.object(service, 'get_config', side_effect=mock_get_config):
        request = TagRemapRequest(
            old_tag="old_tag",
            new_tag="new_tag",
            validate=True  # Enable validation to test full path
        )
        
        await service.remap_tag(request)
        # Success if no exception raised
