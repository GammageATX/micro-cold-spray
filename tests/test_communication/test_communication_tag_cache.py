"""Tests for tag cache service."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from micro_cold_spray.api.base.exceptions import ServiceError, ValidationError
from micro_cold_spray.api.communication.services.tag_cache import TagCacheService
from micro_cold_spray.api.communication.models.tags import TagValue


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    service = AsyncMock()
    service.get_config = AsyncMock()
    return service


@pytest.fixture
def sample_tag_config():
    """Create sample tag configuration."""
    return {
        "tag_groups": {
            "gas_control": {
                "main_flow": {
                    "measured": {
                        "type": "float",
                        "access": "read",
                        "description": "Main gas flow measured",
                        "unit": "SLPM",
                        "range": [0.0, 100.0],
                        "mapped": True
                    },
                    "setpoint": {
                        "type": "float",
                        "access": "read/write",
                        "description": "Main gas flow setpoint",
                        "unit": "SLPM",
                        "range": [0.0, 100.0],
                        "mapped": True
                    },
                    "non_dict_entry": "skip_me"  # Test skipping non-dict entries
                }
            },
            "status": {
                "state": {
                    "type": "string",
                    "access": "read",
                    "description": "System state",
                    "options": ["IDLE", "RUNNING", "ERROR"],
                    "mapped": False
                },
                "enabled": {
                    "type": "bool",
                    "access": "read/write",
                    "description": "System enabled state",
                    "mapped": False
                }
            }
        }
    }


@pytest.fixture
async def tag_cache_service(mock_config_service, sample_tag_config):
    """Create tag cache service instance."""
    mock_config_service.get_config.return_value = sample_tag_config
    service = TagCacheService(mock_config_service)
    await service.start()
    return service


class TestTagCacheService:
    """Test tag cache service functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, tag_cache_service):
        """Test service initialization."""
        # Verify cache was built correctly
        assert "gas_control.main_flow.measured" in tag_cache_service._cache
        assert "gas_control.main_flow.setpoint" in tag_cache_service._cache
        assert "status.state" in tag_cache_service._cache

        # Verify metadata was set correctly
        measured_tag = tag_cache_service._cache["gas_control.main_flow.measured"]
        assert measured_tag.metadata.type == "float"
        assert measured_tag.metadata.access == "read"
        assert measured_tag.metadata.range == [0.0, 100.0]
        assert measured_tag.metadata.unit == "SLPM"
        assert not measured_tag.metadata.internal

        state_tag = tag_cache_service._cache["status.state"]
        assert state_tag.metadata.type == "string"
        assert state_tag.metadata.options == ["IDLE", "RUNNING", "ERROR"]
        assert state_tag.metadata.internal

    @pytest.mark.asyncio
    async def test_initialization_error(self, mock_config_service):
        """Test initialization with error."""
        # Mock the tag mapping service to avoid dependency issues
        with patch('micro_cold_spray.api.communication.services.tag_cache.TagMappingService') as mock_mapping:
            mock_instance = AsyncMock()
            mock_mapping.return_value = mock_instance
            mock_instance.start.side_effect = ServiceError("Failed to start tag mapping")
            
            service = TagCacheService(mock_config_service)
            with pytest.raises(ServiceError) as exc_info:
                await service.start()
            assert "Failed to start tag mapping" in str(exc_info.value)

    def test_update_tag_valid(self, tag_cache_service):
        """Test updating tag with valid value."""
        tag_cache_service.update_tag("gas_control.main_flow.setpoint", 50.0)
        value = tag_cache_service.get_tag("gas_control.main_flow.setpoint")
        assert value == 50.0

    def test_update_tag_invalid_path(self, tag_cache_service):
        """Test updating non-existent tag."""
        with pytest.raises(ValidationError) as exc_info:
            tag_cache_service.update_tag("invalid.tag", 50.0)
        assert "Tag not in cache" in str(exc_info.value)

    def test_update_tag_invalid_type(self, tag_cache_service):
        """Test updating tag with wrong type."""
        with pytest.raises(ValidationError) as exc_info:
            tag_cache_service.update_tag("gas_control.main_flow.setpoint", "invalid")
        assert "Value must be numeric" in str(exc_info.value)

    def test_update_tag_invalid_range(self, tag_cache_service):
        """Test updating tag with out of range value."""
        with pytest.raises(ValidationError) as exc_info:
            tag_cache_service.update_tag("gas_control.main_flow.setpoint", 150.0)
        assert "Value out of range" in str(exc_info.value)

    def test_update_tag_invalid_option(self, tag_cache_service):
        """Test updating tag with invalid option."""
        with pytest.raises(ValidationError) as exc_info:
            tag_cache_service.update_tag("status.state", "INVALID")
        assert "Invalid option" in str(exc_info.value)

    def test_update_tag_invalid_bool(self, tag_cache_service):
        """Test updating boolean tag with invalid value."""
        with pytest.raises(ValidationError) as exc_info:
            tag_cache_service.update_tag("status.enabled", "not_a_bool")
        assert "Value must be boolean" in str(exc_info.value)

    def test_update_tag_unexpected_error(self, tag_cache_service):
        """Test updating tag with unexpected error."""
        with patch.object(tag_cache_service, 'validate_value', side_effect=Exception("Unexpected")):
            with pytest.raises(ServiceError) as exc_info:
                tag_cache_service.update_tag("gas_control.main_flow.setpoint", 50.0)
            assert "Failed to update tag" in str(exc_info.value)

    def test_get_tag_valid(self, tag_cache_service):
        """Test getting tag value."""
        tag_cache_service.update_tag("gas_control.main_flow.setpoint", 50.0)
        value = tag_cache_service.get_tag("gas_control.main_flow.setpoint")
        assert value == 50.0

    def test_get_tag_invalid_path(self, tag_cache_service):
        """Test getting non-existent tag."""
        with pytest.raises(ValidationError) as exc_info:
            tag_cache_service.get_tag("invalid.tag")
        assert "Tag not in cache" in str(exc_info.value)

    def test_get_tag_with_metadata(self, tag_cache_service):
        """Test getting tag with metadata."""
        tag_cache_service.update_tag("gas_control.main_flow.setpoint", 50.0)
        tag_value = tag_cache_service.get_tag_with_metadata("gas_control.main_flow.setpoint")
        
        assert isinstance(tag_value, TagValue)
        assert tag_value.value == 50.0
        assert tag_value.metadata.type == "float"
        assert tag_value.metadata.range == [0.0, 100.0]
        assert isinstance(tag_value.timestamp, datetime)

    def test_get_tag_with_metadata_invalid_path(self, tag_cache_service):
        """Test getting metadata for non-existent tag."""
        with pytest.raises(ValidationError) as exc_info:
            tag_cache_service.get_tag_with_metadata("invalid.tag")
        assert "Tag not in cache" in str(exc_info.value)

    def test_filter_tags_by_group(self, tag_cache_service):
        """Test filtering tags by group."""
        response = tag_cache_service.filter_tags(groups={"gas_control"})
        assert len(response.tags) == 2
        assert "gas_control.main_flow.measured" in response.tags
        assert "gas_control.main_flow.setpoint" in response.tags
        assert "status.state" not in response.tags
        assert response.groups == {"gas_control"}

    def test_filter_tags_by_type(self, tag_cache_service):
        """Test filtering tags by type."""
        response = tag_cache_service.filter_tags(types={"float"})
        assert len(response.tags) == 2
        assert all(tag.metadata.type == "float" for tag in response.tags.values())

    def test_filter_tags_by_access(self, tag_cache_service):
        """Test filtering tags by access."""
        response = tag_cache_service.filter_tags(access={"read/write"})
        assert len(response.tags) == 2  # setpoint and enabled
        assert all(tag.metadata.access == "read/write" for tag in response.tags.values())

    def test_filter_tags_multiple_criteria(self, tag_cache_service):
        """Test filtering tags with multiple criteria."""
        response = tag_cache_service.filter_tags(
            groups={"gas_control"},
            types={"float"},
            access={"read/write"}
        )
        assert len(response.tags) == 1
        assert "gas_control.main_flow.setpoint" in response.tags

    def test_filter_tags_no_matches(self, tag_cache_service):
        """Test filtering tags with no matches."""
        response = tag_cache_service.filter_tags(groups={"invalid_group"})
        assert len(response.tags) == 0
        assert len(response.groups) == 0

    def test_filter_tags_error(self, tag_cache_service):
        """Test filtering tags with error."""
        with patch.dict(tag_cache_service._cache, {"invalid": None}):
            with pytest.raises(ServiceError) as exc_info:
                tag_cache_service.filter_tags()
            assert "Failed to filter tags" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_service_cleanup(self, tag_cache_service):
        """Test service cleanup on stop."""
        await tag_cache_service.stop()
        assert len(tag_cache_service._cache) == 0
        # The tag mapping service is stopped but not set to None
        assert tag_cache_service._tag_mapping is not None
        assert not tag_cache_service._tag_mapping._is_running

    @pytest.mark.asyncio
    async def test_build_cache_error(self, mock_config_service):
        """Test cache building with invalid config."""
        # Mock the tag mapping service to avoid dependency issues
        with patch('micro_cold_spray.api.communication.services.tag_cache.TagMappingService') as mock_mapping:
            mock_instance = AsyncMock()
            mock_mapping.return_value = mock_instance
            mock_instance.start.return_value = None  # Allow tag mapping to start
            
            # Return config that will cause metadata creation to fail
            mock_config_service.get_config.return_value = {
                "tag_groups": {
                    "test": {
                        "tag": {
                            "type": "float",
                            "access": "read",
                            "range": ["invalid", "range"]  # This will cause metadata creation to fail
                        }
                    }
                }
            }
            service = TagCacheService(mock_config_service)
            
            with pytest.raises(ServiceError) as exc_info:
                await service.start()
            assert "Failed to build tag cache" in str(exc_info.value)

    def test_validate_value_invalid_tag(self, tag_cache_service):
        """Test validating value for non-existent tag."""
        with pytest.raises(ValidationError) as exc_info:
            tag_cache_service.validate_value("invalid.tag", 50.0)
        assert "Tag not in cache" in str(exc_info.value)

    def test_validate_value_invalid_string(self, tag_cache_service):
        """Test validating string value with wrong type."""
        with pytest.raises(ValidationError) as exc_info:
            tag_cache_service.validate_value("status.state", 123)
        assert "Value must be string" in str(exc_info.value)
