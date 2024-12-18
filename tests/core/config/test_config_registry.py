"""Tests for registry service."""

import pytest
from unittest.mock import patch
from fastapi import status, HTTPException
from loguru import logger

from micro_cold_spray.api.config.services.registry_service import RegistryService


@pytest.fixture
def registry_service():
    """Create registry service instance."""
    return RegistryService()


@pytest.fixture
def test_data():
    """Create test data with references."""
    return {
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


@pytest.fixture
def test_tags():
    """Create test tag set."""
    return {"tag1", "tag2", "tag3"}


@pytest.fixture
def test_data_with_tags(test_tags):
    """Create test data with tag references."""
    return {
        "tag": "tag1",
        "nested": {
            "tag": "tag2"
        },
        "list": [
            {"tag": "tag3"},
            {"tag": "unknown_tag"}
        ]
    }


@pytest.mark.asyncio
async def test_service_start(registry_service):
    """Test service startup."""
    await registry_service.start()
    assert registry_service.is_running
    assert "read" in registry_service._actions
    assert "range" in registry_service._validations
    
    # Check health
    health = await registry_service._check_health()
    assert health["tags"] == 0  # Empty at start
    assert health["actions"] == 3  # read, write, monitor
    assert health["validations"] == 3  # range, enum, pattern


@pytest.mark.asyncio
async def test_service_start_error():
    """Test service startup with error."""
    service = RegistryService()
    
    # Mock logger.info to raise error
    with patch.object(logger, 'info', side_effect=Exception("Start error")):
        with pytest.raises(HTTPException) as exc_info:
            await service.start()
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Start error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_validate_references_valid(registry_service, test_data):
    """Test validating valid references."""
    await registry_service.start()
    
    result = await registry_service.validate_references(test_data)
    assert result.valid
    assert not result.errors
    assert not result.warnings


@pytest.mark.asyncio
async def test_validate_references_invalid(registry_service):
    """Test validating invalid references."""
    await registry_service.start()
    
    invalid_data = {
        "action": "invalid_action",
        "validation": "invalid_validation",
        "nested": {
            "action": "write",  # valid
            "validation": "unknown"  # invalid
        }
    }
    
    result = await registry_service.validate_references(invalid_data)
    assert not result.valid
    assert len(result.errors) > 0
    assert any("Unknown action reference" in error for error in result.errors)
    assert any("Unknown validation reference" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_references_with_tags(registry_service, test_tags, test_data_with_tags):
    """Test validating tag references."""
    await registry_service.start()
    
    # Add test tags to registry
    registry_service._tags = test_tags
    
    result = await registry_service.validate_references(test_data_with_tags)
    assert not result.valid
    assert len(result.errors) > 0
    assert any("Unknown tag reference" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_references_with_error(registry_service):
    """Test validation with unexpected error."""
    await registry_service.start()
    
    with patch.object(registry_service, '_validate_tag_references', side_effect=Exception("Unexpected error")):
        with pytest.raises(HTTPException) as exc_info:
            await registry_service.validate_references({"tag": "test"})
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Reference validation failed" in str(exc_info.value.detail)


@pytest.mark.parametrize("registry_attr,check_method,error_message", [
    ("_tags", "_tag_exists", "Failed to check tag existence"),
    ("_actions", "_action_exists", "Failed to check action existence"),
    ("_validations", "_validation_exists", "Failed to check validation existence")
])
def test_existence_check_errors(registry_service, registry_attr, check_method, error_message):
    """Test existence check errors for tags, actions, and validations."""
    setattr(registry_service, registry_attr, None)  # Force error
    
    with pytest.raises(HTTPException) as exc_info:
        getattr(registry_service, check_method)("test")
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert error_message in str(exc_info.value.detail)


@pytest.mark.parametrize("load_method,error_message", [
    ("_load_tag_registry", "Failed to load tag registry"),
    ("_load_action_registry", "Failed to load action registry"),
    ("_load_validation_registry", "Failed to load validation registry")
])
@pytest.mark.asyncio
async def test_registry_load_errors(load_method, error_message):
    """Test registry loading errors."""
    service = RegistryService()
    
    with patch.object(logger, 'info', side_effect=Exception("Load error")):
        with pytest.raises(HTTPException) as exc_info:
            await getattr(service, load_method)()
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error_message in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_validate_reference_complex_data(registry_service):
    """Test validating references in complex nested data."""
    await registry_service.start()
    
    complex_data = {
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
    
    result = await registry_service.validate_references(complex_data)
    assert result.valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_reference_mixed_types(registry_service):
    """Test validating references with mixed data types."""
    await registry_service.start()
    
    mixed_data = {
        "string": "simple string",
        "number": 42,
        "boolean": True,
        "none": None,
        "action": "read",
        "list": [1, "string", {"validation": "range"}]
    }
    
    result = await registry_service.validate_references(mixed_data)
    assert result.valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_reference_validation_error(registry_service):
    """Test validation with validation error."""
    await registry_service.start()
    
    # Mock _validate_tag_references to raise HTTPException
    def mock_validate(*args, **kwargs):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Test error"
        )
    
    with patch.object(registry_service, '_validate_tag_references', side_effect=mock_validate):
        with pytest.raises(HTTPException) as exc_info:
            await registry_service.validate_references({"tag": "test"})
        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Test error" in str(exc_info.value.detail)
