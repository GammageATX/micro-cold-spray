"""Tests for config models."""

import pytest
from datetime import datetime

from micro_cold_spray.api.config.models import (
    ConfigData,
    ConfigMetadata,
    ConfigSchema,
    FormatMetadata,
    ConfigReference,
    ConfigValidationResult,
    ConfigUpdate
)


def test_config_data_get_simple():
    """Test getting simple values from config data."""
    config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now()
        ),
        data={
            "key1": "value1",
            "key2": 123,
            "key3": True
        }
    )
    
    assert config.get("key1") == "value1"
    assert config.get("key2") == 123
    assert config.get("key3") is True
    assert config.get("nonexistent") is None
    assert config.get("nonexistent", "default") == "default"


def test_config_data_get_nested():
    """Test getting nested values from config data."""
    config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now()
        ),
        data={
            "level1": {
                "level2": {
                    "level3": "nested_value"
                }
            }
        }
    )
    
    assert config.get("level1.level2.level3") == "nested_value"
    assert config.get("level1.level2.nonexistent") is None
    assert config.get("level1.nonexistent.level3") is None
    assert config.get("nonexistent.level2.level3") is None


def test_config_data_get_non_dict_values():
    """Test getting values when intermediate nodes are not dictionaries."""
    config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now()
        ),
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
    
    # Test accessing through non-dict values
    assert config.get("string_value.anything") is None
    assert config.get("list_value.anything") is None
    assert config.get("number_value.anything") is None
    assert config.get("bool_value.anything") is None
    assert config.get("none_value.anything") is None
    
    # Test valid nested access still works
    assert config.get("nested.valid") == "value"


def test_config_data_get_empty_key():
    """Test getting values with empty or invalid keys."""
    config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now()
        ),
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
    config = ConfigData(
        metadata=ConfigMetadata(
            config_type="test",
            last_modified=datetime.now()
        ),
        data={}
    )
    # Manually set data to non-dict to bypass Pydantic validation
    config.data = "not_a_dict"  # type: ignore
    
    assert config.get("any_key") is None
    assert config.get("any_key", "default") == "default"


def test_config_schema_type_validation():
    """Test ConfigSchema type validation."""
    # Valid types
    valid_types = ['string', 'number', 'boolean', 'object', 'array', 'state', 'tag', 'action', 'sequence']
    for type_name in valid_types:
        schema = ConfigSchema(type=type_name)
        assert schema.type == type_name
    
    # Invalid type
    with pytest.raises(ValueError) as exc_info:
        ConfigSchema(type="invalid_type")
    assert "Type must be one of" in str(exc_info.value)


def test_format_metadata():
    """Test FormatMetadata model."""
    metadata = FormatMetadata(
        description="Test format",
        examples=["example1", "example2"]
    )
    
    assert metadata.description == "Test format"
    assert metadata.examples == ["example1", "example2"]


def test_config_reference():
    """Test ConfigReference model."""
    reference = ConfigReference(
        config_type="test",
        path="path.to.value"
    )
    
    assert reference.config_type == "test"
    assert reference.path == "path.to.value"
    assert reference.required is True  # Default value


def test_config_validation_result():
    """Test ConfigValidationResult model."""
    result = ConfigValidationResult(
        valid=True,
        errors=[],
        warnings=["Warning message"]
    )
    
    assert result.valid is True
    assert len(result.errors) == 0
    assert result.warnings == ["Warning message"]


def test_config_update():
    """Test ConfigUpdate model."""
    update = ConfigUpdate(
        config_type="test",
        data={"key": "value"}
    )
    
    assert update.config_type == "test"
    assert update.data == {"key": "value"}
    assert update.backup is True  # Default value
    assert update.should_validate is True  # Default value
