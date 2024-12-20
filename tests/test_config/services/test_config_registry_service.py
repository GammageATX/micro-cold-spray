"""Tests for registry service."""

import pytest
from unittest.mock import patch
from loguru import logger

from micro_cold_spray.api.config.services.config_registry_service import ConfigRegistryService
from micro_cold_spray.api.base.base_errors import ConfigError, ValidationError


@pytest.fixture
def registry_service():
    """Create registry service instance."""
    return ConfigRegistryService(service_name="registry")


@pytest.mark.asyncio
async def test_service_start(registry_service):
    """Test service startup."""
    await registry_service.start()
    assert registry_service.is_running
    assert "read" in registry_service._actions
    assert "range" in registry_service._validations


@pytest.mark.asyncio
async def test_service_start_error():
    """Test service startup with error."""
    service = ConfigRegistryService(service_name="registry")
    
    # Mock logger.info to raise error
    with patch.object(logger, 'info', side_effect=Exception("Start error")):
        with pytest.raises(ConfigError, match="Failed to start registry service"):
            await service.start()


@pytest.mark.asyncio
async def test_validate_references_valid(registry_service):
    """Test validating valid references."""
    await registry_service.start()
    
    data = {
        "action": "read",
        "validation": "range",
        "nested": {
            "action": "write",
            "validation": "enum"
        },
        "list": [
            {"action": "monitor"},
            {"validation": "pattern"}
        ]
    }
    
    result = await registry_service.validate_references(data)
    assert result.valid
    assert not result.errors
    assert not result.warnings


@pytest.mark.asyncio
async def test_validate_references_invalid(registry_service):
    """Test validating invalid references."""
    await registry_service.start()
    
    data = {
        "action": "invalid_action",
        "validation": "invalid_validation",
        "nested": {
            "action": "write",  # valid
            "validation": "unknown"  # invalid
        }
    }
    
    result = await registry_service.validate_references(data)
    assert not result.valid
    assert len(result.errors) > 0
    assert any("Unknown action reference" in error for error in result.errors)
    assert any("Unknown validation reference" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_references_with_tags(registry_service):
    """Test validating tag references."""
    await registry_service.start()
    
    # Add some test tags
    registry_service._tags = {"tag1", "tag2"}
    
    data = {
        "tag": "tag1",
        "nested": {
            "tag": "tag2"
        },
        "invalid": {
            "tag": "unknown_tag"
        }
    }
    
    result = await registry_service.validate_references(data)
    assert not result.valid
    assert len(result.errors) > 0
    assert any("Unknown tag reference" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_references_with_error(registry_service):
    """Test validation with unexpected error."""
    await registry_service.start()
    
    with patch.object(registry_service, '_validate_tag_references', side_effect=Exception("Unexpected error")):
        with pytest.raises(ValidationError, match="Reference validation failed"):
            await registry_service.validate_references({"tag": "test"})


def test_tag_exists_error(registry_service):
    """Test tag existence check with error."""
    registry_service._tags = None  # Force error
    
    with pytest.raises(ValidationError, match="Failed to check tag existence"):
        registry_service._tag_exists("test")


def test_action_exists_error(registry_service):
    """Test action existence check with error."""
    registry_service._actions = None  # Force error
    
    with pytest.raises(ValidationError, match="Failed to check action existence"):
        registry_service._action_exists("test")


def test_validation_exists_error(registry_service):
    """Test validation existence check with error."""
    registry_service._validations = None  # Force error
    
    with pytest.raises(ValidationError, match="Failed to check validation existence"):
        registry_service._validation_exists("test")


@pytest.mark.asyncio
async def test_load_tag_registry_error():
    """Test tag registry loading with error."""
    service = ConfigRegistryService(service_name="registry")
    
    with patch.object(logger, 'info', side_effect=Exception("Load error")):
        with pytest.raises(ConfigError, match="Failed to load tag registry"):
            await service._load_tag_registry()


@pytest.mark.asyncio
async def test_load_action_registry_error():
    """Test action registry loading with error."""
    service = ConfigRegistryService(service_name="registry")
    
    with patch.object(logger, 'info', side_effect=Exception("Load error")):
        with pytest.raises(ConfigError, match="Failed to load action registry"):
            await service._load_action_registry()


@pytest.mark.asyncio
async def test_load_validation_registry_error():
    """Test validation registry loading with error."""
    service = ConfigRegistryService(service_name="registry")
    
    with patch.object(logger, 'info', side_effect=Exception("Load error")):
        with pytest.raises(ConfigError, match="Failed to load validation registry"):
            await service._load_validation_registry()


@pytest.mark.asyncio
async def test_validate_reference_complex_data(registry_service):
    """Test validating references in complex nested data."""
    await registry_service.start()
    
    data = {
        "level1": {
            "action": "read",
            "list": [
                {"validation": "range"},
                {
                    "nested": {
                        "action": "write",
                        "deep": [
                            {"validation": "pattern"}
                        ]
                    }
                }
            ]
        }
    }
    
    result = await registry_service.validate_references(data)
    assert result.valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_reference_mixed_types(registry_service):
    """Test validating references with mixed data types."""
    await registry_service.start()
    
    data = {
        "string": "simple string",
        "number": 42,
        "boolean": True,
        "none": None,
        "action": "read",
        "list": [1, "string", {"validation": "range"}]
    }
    
    result = await registry_service.validate_references(data)
    assert result.valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_reference_validation_error(registry_service):
    """Test validation with validation error."""
    await registry_service.start()
    
    # Mock _validate_tag_references to raise ValidationError
    def mock_validate(*args, **kwargs):
        raise ValidationError("Test error", {"test": "data"})
    
    with patch.object(registry_service, '_validate_tag_references', side_effect=mock_validate):
        result = await registry_service.validate_references({"test": "data"})
        assert not result.valid
        assert len(result.errors) == 1
        assert "Test error" in result.errors[0]


@pytest.mark.asyncio
async def test_validate_reference_unexpected_error(registry_service):
    """Test validation with unexpected error in reference validation."""
    await registry_service.start()
    
    # Mock _validate_tag_references to raise unexpected error
    with patch.object(registry_service, '_validate_tag_references', side_effect=Exception("Unexpected test error")):
        with pytest.raises(ValidationError, match="Reference validation failed"):
            await registry_service.validate_references({"test": "data"})


@pytest.mark.asyncio
async def test_validate_reference_list_error(registry_service):
    """Test validation with error in list validation."""
    await registry_service.start()
    
    # Create a list with an invalid reference that will trigger an error
    data = {
        "list": [
            {"action": "invalid_action"}
        ]
    }
    
    result = await registry_service.validate_references(data)
    assert not result.valid
    assert len(result.errors) > 0
    assert any("Unknown action reference" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_tag_references_error(registry_service):
    """Test tag reference validation with error."""
    await registry_service.start()
    
    # Mock _validate_reference to raise unexpected error
    def mock_validate(*args, **kwargs):
        raise Exception("Tag validation error")
    
    with patch.object(registry_service, '_validate_reference', side_effect=mock_validate):
        with pytest.raises(ValidationError, match="Tag reference validation failed"):
            registry_service._validate_tag_references({"tag": "test"}, "", [])


@pytest.mark.asyncio
async def test_validate_action_references_error(registry_service):
    """Test action reference validation with error."""
    await registry_service.start()
    
    # Mock _validate_reference to raise unexpected error
    def mock_validate(*args, **kwargs):
        raise Exception("Action validation error")
    
    with patch.object(registry_service, '_validate_reference', side_effect=mock_validate):
        with pytest.raises(ValidationError, match="Action reference validation failed"):
            registry_service._validate_action_references({"action": "test"}, "", [])


@pytest.mark.asyncio
async def test_validate_validation_references_error(registry_service):
    """Test validation reference validation with error."""
    await registry_service.start()
    
    # Mock _validate_reference to raise unexpected error
    def mock_validate(*args, **kwargs):
        raise Exception("Validation reference error")
    
    with patch.object(registry_service, '_validate_reference', side_effect=mock_validate):
        with pytest.raises(ValidationError, match="Validation reference validation failed"):
            registry_service._validate_validation_references({"validation": "test"}, "", [])


@pytest.mark.asyncio
async def test_validate_reference_internal_error(registry_service):
    """Test validation with internal error in reference validation."""
    await registry_service.start()
    
    # Create a test case that will trigger the error branch
    data = {"action": "test"}  # Direct action reference
    errors = []
    
    # Mock _action_exists to raise an unexpected error
    with patch.object(registry_service, '_action_exists', side_effect=Exception("Internal error")):
        with pytest.raises(ValidationError) as exc_info:
            registry_service._validate_reference(
                data,
                "test_path",
                "action",
                "action",
                registry_service._action_exists,
                errors
            )
        
        assert "Reference validation failed" in str(exc_info.value)
        assert "test_path" in str(exc_info.value.context)
        assert "action" in str(exc_info.value.context)
