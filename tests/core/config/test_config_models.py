"""Tests for config models."""

import pytest
from pydantic import ValidationError
from datetime import datetime

from micro_cold_spray.api.config.models import (
    ConfigSchema,
    ConfigMetadata,
    ConfigData,
    ConfigUpdate,
    ConfigStatus,
    TagRemapRequest,
    ConfigFieldInfo
)
from .helpers import create_config_data


@pytest.fixture
def sample_config_data():
    """Create a sample config data for testing."""
    return create_config_data(
        name="test",
        data={
            "key1": "value1",
            "key2": 123,
            "key3": True,
            "nested": {
                "key": "value"
            }
        }
    )


@pytest.fixture
def nested_config_data():
    """Create a deeply nested config data for testing."""
    return create_config_data(
        name="test",
        data={
            "level1": {
                "level2": {
                    "level3": "nested_value"
                }
            }
        }
    )


@pytest.fixture
def non_dict_config_data():
    """Create config data with non-dictionary values."""
    return create_config_data(
        name="test",
        data={
            "string_value": "not_a_dict",
            "list_value": ["not", "a", "dict"],
            "number_value": 123,
            "bool_value": True,
            "none_value": None,
            "nested": {
                "valid": "value"
            }
        }
    )


def test_config_schema_validation():
    """Test ConfigSchema validation."""
    # Test valid schema
    valid_schema = {
        "type": "object",
        "title": "Test Schema",
        "required": ["field1"],
        "properties": {
            "field1": {"type": "string"},
            "field2": {"type": "number"}
        }
    }
    schema = ConfigSchema(**valid_schema)
    assert schema.type == "object"
    assert schema.title == "Test Schema"
    assert schema.required == ["field1"]
    
    # Test invalid type
    with pytest.raises(ValidationError) as exc_info:
        ConfigSchema(type="invalid_type")
    assert "Type must be one of" in str(exc_info.value)
    
    # Test invalid required field
    with pytest.raises(ValidationError):
        ConfigSchema(
            type="object",
            required="not_a_list"  # Should be a list
        )
    
    # Test nested schema validation
    nested_schema = {
        "type": "object",
        "properties": {
            "nested": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"}
                }
            }
        }
    }
    schema = ConfigSchema(**nested_schema)
    assert schema.properties["nested"].type == "object"


def test_config_metadata_validation():
    """Test ConfigMetadata validation."""
    # Test valid metadata
    valid_metadata = {
        "config_type": "test",
        "last_modified": datetime.now(),
        "version": "1.0.0",
        "description": "Test config"
    }
    metadata = ConfigMetadata(**valid_metadata)
    assert metadata.config_type == "test"
    assert metadata.version == "1.0.0"
    
    # Test missing required fields
    with pytest.raises(ValidationError) as exc_info:
        ConfigMetadata(last_modified=datetime.now())
    assert "config_type" in str(exc_info.value)
    
    # Test invalid version format
    with pytest.raises(ValidationError):
        ConfigMetadata(
            config_type="test",
            last_modified=datetime.now(),
            version="invalid"
        )


def test_config_data_validation():
    """Test ConfigData validation."""
    # Test valid config data
    valid_data = {
        "metadata": {
            "config_type": "test",
            "last_modified": datetime.now(),
            "version": "1.0.0"
        },
        "data": {"key": "value"}
    }
    config = ConfigData(**valid_data)
    assert config.metadata.config_type == "test"
    assert config.data == {"key": "value"}
    
    # Test missing metadata
    with pytest.raises(ValidationError) as exc_info:
        ConfigData(data={"key": "value"})
    assert "metadata" in str(exc_info.value)
    
    # Test invalid data type
    with pytest.raises(ValidationError):
        ConfigData(
            metadata=valid_data["metadata"],
            data="not_a_dict"  # Should be a dict
        )


def test_config_update_validation():
    """Test ConfigUpdate validation."""
    # Test valid update
    valid_update = {
        "config_type": "test",
        "data": {"key": "value"},
        "backup": True,
        "should_validate": True
    }
    update = ConfigUpdate(**valid_update)
    assert update.config_type == "test"
    assert update.data == {"key": "value"}
    
    # Test missing required fields
    with pytest.raises(ValidationError) as exc_info:
        ConfigUpdate(data={"key": "value"})
    assert "config_type" in str(exc_info.value)
    
    # Test invalid data type
    with pytest.raises(ValidationError):
        ConfigUpdate(
            config_type="test",
            data="not_a_dict"  # Should be a dict
        )


def test_config_status_validation():
    """Test ConfigStatus validation."""
    # Test valid status
    valid_status = {
        "is_running": True,
        "cache_size": 10,
        "last_error": "No error",
        "last_update": datetime.now()
    }
    status = ConfigStatus(**valid_status)
    assert status.is_running is True
    assert status.cache_size == 10
    
    # Test missing required fields
    with pytest.raises(ValidationError) as exc_info:
        ConfigStatus(cache_size=10)
    assert "is_running" in str(exc_info.value)
    
    # Test invalid field types
    with pytest.raises(ValidationError):
        ConfigStatus(
            is_running=True,
            cache_size="not_a_number"  # Should be an integer
        )


def test_tag_remap_request_validation():
    """Test TagRemapRequest validation."""
    # Test valid request
    valid_request = {
        "old_tag": "old_tag",
        "new_tag": "new_tag",
        "should_validate": True
    }
    request = TagRemapRequest(**valid_request)
    assert request.old_tag == "old_tag"
    assert request.new_tag == "new_tag"
    
    # Test missing required fields
    with pytest.raises(ValidationError) as exc_info:
        TagRemapRequest(old_tag="old_tag")
    assert "new_tag" in str(exc_info.value)


def test_config_field_info_validation():
    """Test ConfigFieldInfo validation."""
    # Test valid field info
    valid_info = {
        "path": "test.path",
        "type": "string",
        "description": "Test field",
        "constraints": {"min_length": 1},
        "current_value": "test"
    }
    info = ConfigFieldInfo(**valid_info)
    assert info.path == "test.path"
    assert info.type == "string"
    
    # Test missing required fields
    with pytest.raises(ValidationError) as exc_info:
        ConfigFieldInfo(
            path="test.path",
            type="string"
        )
    assert "constraints" in str(exc_info.value)
    
    # Test invalid constraints type
    with pytest.raises(ValidationError):
        ConfigFieldInfo(
            path="test.path",
            type="string",
            description="Test",
            constraints="not_a_dict",  # Should be a dict
            current_value="test"
        )


def test_config_data_get_simple(sample_config_data):
    """Test getting simple values from config data."""
    assert sample_config_data.get("key1") == "value1"
    assert sample_config_data.get("key2") == 123
    assert sample_config_data.get("key3") is True
    assert sample_config_data.get("nonexistent") is None
    assert sample_config_data.get("nonexistent", "default") == "default"


def test_config_data_get_nested(nested_config_data):
    """Test getting nested values from config data."""
    assert nested_config_data.get("level1.level2.level3") == "nested_value"
    assert nested_config_data.get("level1.level2.nonexistent") is None
    assert nested_config_data.get("level1.nonexistent.level3") is None
    assert nested_config_data.get("nonexistent.level2.level3") is None


def test_config_data_get_non_dict_values(non_dict_config_data):
    """Test getting values when intermediate nodes are not dictionaries."""
    # Test accessing through non-dict values
    assert non_dict_config_data.get("string_value.anything") is None
    assert non_dict_config_data.get("list_value.anything") is None
    assert non_dict_config_data.get("number_value.anything") is None
    assert non_dict_config_data.get("bool_value.anything") is None
    assert non_dict_config_data.get("none_value.anything") is None
    
    # Test valid nested access still works
    assert non_dict_config_data.get("nested.valid") == "value"


def test_config_data_get_empty_key():
    """Test getting values with empty or invalid keys."""
    config = create_config_data(
        name="test",
        data={
            "": "empty_key",
            "normal": "value"
        }
    )
    
    assert config.get("") == "empty_key"
    assert config.get(".") is None
    assert config.get("..") is None
    assert config.get("normal.") is None
    assert config.get(".normal") is None


def test_config_data_get_non_dict_data():
    """Test getting values when data is not a dictionary."""
    config = create_config_data(name="test", data={})
    # Manually set data to non-dict to bypass Pydantic validation
    config.data = "not_a_dict"  # type: ignore
    
    assert config.get("any_key") is None
    assert config.get("any_key", "default") == "default"
