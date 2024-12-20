"""Tests for schema service."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from micro_cold_spray.api.config.services.config_schema_service import ConfigSchemaService
from micro_cold_spray.api.base.base_errors import ConfigError
from micro_cold_spray.api.config.models import ConfigSchema


@pytest.fixture
def schema_dir(tmp_path):
    """Create temporary schema directory."""
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    return schema_dir


@pytest.fixture
def schema_service(schema_dir):
    """Create schema service instance."""
    return ConfigSchemaService(service_name="schema", schema_dir=schema_dir)


@pytest.fixture
def sample_schema():
    """Create sample schema data."""
    return {
        "type": "object",
        "title": "Test Configuration",
        "description": "Schema for testing",
        "properties": {
            "name": {"type": "string"},
            "value": {"type": "number"}
        },
        "required": ["name", "value"]
    }


@pytest.mark.asyncio
async def test_service_start(schema_service):
    """Test service startup."""
    await schema_service.start()
    assert schema_service.is_running
    assert isinstance(schema_service._schemas, dict)


@pytest.mark.asyncio
async def test_service_start_error():
    """Test service startup with error."""
    # Mock _load_schemas to raise an error
    service = ConfigSchemaService(service_name="schema", schema_dir=Path("/tmp/schemas"))
    with patch.object(service, '_load_schemas', side_effect=Exception("Load error")):
        with pytest.raises(ConfigError, match="Failed to start schema service"):
            await service.start()


@pytest.mark.asyncio
async def test_load_schemas(schema_dir, sample_schema):
    """Test loading schemas from files."""
    # Create a test schema file
    schema_file = schema_dir / "test.json"
    with open(schema_file, "w") as f:
        json.dump(sample_schema, f)

    service = ConfigSchemaService(service_name="schema", schema_dir=schema_dir)
    await service.start()

    assert "test" in service._schemas
    loaded_schema = service._schemas["test"]
    assert isinstance(loaded_schema, ConfigSchema)
    assert loaded_schema.type == "object"
    assert loaded_schema.title == "Test Configuration"


@pytest.mark.asyncio
async def test_load_schemas_invalid_format(schema_dir):
    """Test loading invalid schema format."""
    # Create invalid schema file (array instead of object)
    schema_file = schema_dir / "invalid.json"
    with open(schema_file, "w") as f:
        json.dump(["invalid"], f)

    service = ConfigSchemaService(service_name="schema", schema_dir=schema_dir)
    with pytest.raises(ConfigError, match="Failed to start schema service"):
        await service.start()


@pytest.mark.asyncio
async def test_load_schemas_invalid_json(schema_dir):
    """Test loading invalid JSON file."""
    # Create invalid JSON file
    schema_file = schema_dir / "invalid.json"
    with open(schema_file, "w") as f:
        f.write("invalid json")

    service = ConfigSchemaService(service_name="schema", schema_dir=schema_dir)
    with pytest.raises(ConfigError, match="Failed to start schema service"):
        await service.start()


def test_get_schema(schema_service, sample_schema):
    """Test getting schema by type."""
    schema_service._schemas["test"] = ConfigSchema(**sample_schema)
    
    # Test existing schema
    schema = schema_service.get_schema("test")
    assert schema is not None
    assert isinstance(schema, ConfigSchema)
    assert schema.type == "object"
    
    # Test non-existent schema
    assert schema_service.get_schema("nonexistent") is None


def test_build_schema(schema_service, sample_schema):
    """Test building schema from raw data."""
    schema = schema_service.build_schema(sample_schema)
    assert isinstance(schema, ConfigSchema)
    assert schema.type == "object"
    assert schema.title == "Test Configuration"
    assert "name" in schema.properties
    assert "value" in schema.properties


def test_build_schema_invalid(schema_service):
    """Test building schema with invalid data."""
    with pytest.raises(Exception):  # Should raise validation error from pydantic
        schema_service.build_schema({"invalid": "schema"})


@pytest.mark.asyncio
async def test_validate_config(schema_service, sample_schema):
    """Test configuration validation."""
    schema_service._schemas["test"] = ConfigSchema(**sample_schema)
    
    # Valid config
    valid_config = {
        "name": "test",
        "value": 42
    }
    errors = schema_service.validate_config("test", valid_config)
    assert len(errors) == 0
    
    # Invalid config - missing required field
    invalid_config = {
        "name": "test"
    }
    errors = schema_service.validate_config("test", invalid_config)
    assert len(errors) > 0
    assert any("value" in error for error in errors)
    
    # Invalid config - wrong type
    invalid_config = {
        "name": "test",
        "value": "not a number"
    }
    errors = schema_service.validate_config("test", invalid_config)
    assert len(errors) > 0
    assert any("value" in error for error in errors)


@pytest.mark.asyncio
async def test_validate_config_schema_not_found(schema_service):
    """Test validation with non-existent schema."""
    with pytest.raises(ConfigError, match="Schema not found"):
        schema_service.validate_config("nonexistent", {})


@pytest.mark.asyncio
async def test_validate_config_unexpected_error(schema_service, sample_schema):
    """Test validation with unexpected error."""
    schema_service._schemas["test"] = ConfigSchema(**sample_schema)
    
    # Mock _validate_against_schema to raise unexpected error
    with patch.object(schema_service, '_validate_against_schema', side_effect=Exception("Unexpected")):
        with pytest.raises(ConfigError, match="Validation failed"):
            schema_service.validate_config("test", {})


@pytest.mark.asyncio
async def test_validate_nested_config(schema_service):
    """Test validation of nested configuration."""
    nested_schema = {
        "type": "object",
        "title": "Nested Configuration",
        "properties": {
            "name": {"type": "string"},
            "settings": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "values": {
                        "type": "array",
                        "items": {"type": "number"}
                    }
                },
                "required": ["enabled", "values"]
            }
        },
        "required": ["name", "settings"]
    }
    schema_service._schemas["nested"] = ConfigSchema(**nested_schema)
    
    # Valid nested config
    valid_config = {
        "name": "test",
        "settings": {
            "enabled": True,
            "values": [1, 2, 3]
        }
    }
    errors = schema_service.validate_config("nested", valid_config)
    assert len(errors) == 0
    
    # Invalid nested config - wrong type in array
    invalid_config = {
        "name": "test",
        "settings": {
            "enabled": True,
            "values": [1, "two", 3]
        }
    }
    errors = schema_service.validate_config("nested", invalid_config)
    assert len(errors) > 0
    assert any("values" in error for error in errors)


@pytest.mark.asyncio
async def test_validate_array_config(schema_service):
    """Test validation of array configuration."""
    array_schema = {
        "type": "object",
        "title": "Array Configuration",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "count": {"type": "number"}
                    },
                    "required": ["id", "count"]
                }
            }
        },
        "required": ["items"]
    }
    schema_service._schemas["array"] = ConfigSchema(**array_schema)
    
    # Valid array config
    valid_config = {
        "items": [
            {"id": "item1", "count": 1},
            {"id": "item2", "count": 2}
        ]
    }
    errors = schema_service.validate_config("array", valid_config)
    assert len(errors) == 0
    
    # Invalid array config - missing required field
    invalid_config = {
        "items": [
            {"id": "item1", "count": 1},
            {"id": "item2"}  # Missing count
        ]
    }
    errors = schema_service.validate_config("array", invalid_config)
    assert len(errors) > 0
    assert any("count" in error for error in errors)


@pytest.mark.asyncio
async def test_validate_optional_fields(schema_service):
    """Test validation of optional fields."""
    optional_schema = {
        "type": "object",
        "title": "Optional Configuration",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"}
                }
            }
        },
        "required": ["required_field"]
    }
    schema_service._schemas["optional"] = ConfigSchema(**optional_schema)
    
    # Config with only required field
    valid_config = {
        "required_field": "test"
    }
    errors = schema_service.validate_config("optional", valid_config)
    assert len(errors) == 0
    
    # Config with optional field
    valid_config_with_optional = {
        "required_field": "test",
        "optional_field": {
            "value": 42
        }
    }
    errors = schema_service.validate_config("optional", valid_config_with_optional)
    assert len(errors) == 0
    
    # Invalid optional field type
    invalid_config = {
        "required_field": "test",
        "optional_field": {
            "value": "not a number"
        }
    }
    errors = schema_service.validate_config("optional", invalid_config)
    assert len(errors) > 0
    assert any("value" in error for error in errors)


def test_validate_string_constraints(schema_service):
    """Test string validation with pattern and enum constraints."""
    string_schema = {
        "type": "object",
        "properties": {
            "pattern_field": {
                "type": "string",
                "pattern": r"^[A-Z][a-z]+$"  # Capitalized word
            },
            "enum_field": {
                "type": "string",
                "enum": ["red", "green", "blue"]
            }
        }
    }
    schema_service._schemas["string"] = ConfigSchema(**string_schema)
    
    # Valid values
    valid_config = {
        "pattern_field": "Hello",
        "enum_field": "red"
    }
    errors = schema_service.validate_config("string", valid_config)
    assert len(errors) == 0
    
    # Invalid pattern
    invalid_pattern = {
        "pattern_field": "hello",  # Not capitalized
        "enum_field": "red"
    }
    errors = schema_service.validate_config("string", invalid_pattern)
    assert any("pattern" in error for error in errors)
    
    # Invalid enum
    invalid_enum = {
        "pattern_field": "Hello",
        "enum_field": "yellow"  # Not in enum
    }
    errors = schema_service.validate_config("string", invalid_enum)
    assert any("enum" in error for error in errors)


def test_validate_number_constraints(schema_service):
    """Test number validation with min/max constraints."""
    number_schema = {
        "type": "object",
        "properties": {
            "bounded_number": {
                "type": "number",
                "min_value": 0,
                "max_value": 100
            }
        }
    }
    schema_service._schemas["number"] = ConfigSchema(**number_schema)
    
    # Valid number
    valid_config = {"bounded_number": 50}
    errors = schema_service.validate_config("number", valid_config)
    assert len(errors) == 0
    
    # Below minimum
    below_min = {"bounded_number": -1}
    errors = schema_service.validate_config("number", below_min)
    assert any("must be >=" in error for error in errors)
    
    # Above maximum
    above_max = {"bounded_number": 101}
    errors = schema_service.validate_config("number", above_max)
    assert any("must be <=" in error for error in errors)
    
    # Invalid type
    invalid_type = {"bounded_number": "50"}  # String instead of number
    errors = schema_service.validate_config("number", invalid_type)
    assert any("Expected number" in error for error in errors)


def test_validate_boolean(schema_service):
    """Test boolean validation."""
    bool_schema = {
        "type": "object",
        "properties": {
            "flag": {"type": "boolean"}
        }
    }
    schema_service._schemas["boolean"] = ConfigSchema(**bool_schema)
    
    # Valid boolean values
    valid_true = {"flag": True}
    valid_false = {"flag": False}
    assert len(schema_service.validate_config("boolean", valid_true)) == 0
    assert len(schema_service.validate_config("boolean", valid_false)) == 0
    
    # Invalid values
    invalid_string = {"flag": "true"}  # String instead of boolean
    invalid_number = {"flag": 1}  # Number instead of boolean
    assert any("Expected boolean" in error for error in schema_service.validate_config("boolean", invalid_string))
    assert any("Expected boolean" in error for error in schema_service.validate_config("boolean", invalid_number))


def test_validate_references(schema_service):
    """Test validation of tag/action/state/sequence references."""
    ref_schema = {
        "type": "object",
        "properties": {
            "tag_ref": {
                "type": "tag",
                "references": ["tag1", "tag2"]
            },
            "action_ref": {
                "type": "action",
                "references": ["start", "stop"]
            },
            "state_ref": {
                "type": "state",
                "references": ["idle", "running"]
            }
        }
    }
    schema_service._schemas["references"] = ConfigSchema(**ref_schema)
    
    # Valid references
    valid_config = {
        "tag_ref": "tag1",
        "action_ref": "start",
        "state_ref": "idle"
    }
    errors = schema_service.validate_config("references", valid_config)
    assert len(errors) == 0
    
    # Invalid references
    invalid_config = {
        "tag_ref": "unknown_tag",
        "action_ref": "unknown_action",
        "state_ref": "unknown_state"
    }
    errors = schema_service.validate_config("references", invalid_config)
    assert len(errors) == 3  # One error for each invalid reference
    assert any("Invalid reference" in error for error in errors)


def test_validate_dependencies(schema_service):
    """Test validation of dependencies."""
    dep_schema = {
        "type": "object",
        "properties": {
            "main_tag": {
                "type": "tag",
                "dependencies": ["sub_tag1", "sub_tag2"]
            }
        }
    }
    schema_service._schemas["dependencies"] = ConfigSchema(**dep_schema)
    
    # Test with missing dependencies
    config = {
        "main_tag": "test_tag"  # Missing required sub-tags
    }
    errors = schema_service.validate_config("dependencies", config)
    assert len(errors) == 2  # One error for each missing dependency
    assert all("Missing dependency" in error for error in errors)


def test_validate_unknown_type(schema_service):
    """Test validation with unknown schema type."""
    # Test unknown type validation directly
    schema = ConfigSchema(type="object")  # Valid schema type
    data = {"test": "value"}
    errors = []
    
    # Call internal validation with unknown type
    schema_service._validate_against_schema(data, schema, "", errors)
    assert len(errors) == 0  # No errors for valid type
    
    # Test with unknown type (bypassing Pydantic validation)
    schema.type = "unknown_type"  # Modify type after creation
    schema_service._validate_against_schema(data, schema, "", errors)
    assert len(errors) == 1
    assert "Unknown schema type" in errors[0]


@pytest.mark.asyncio
async def test_schema_loading(tmp_path):
    """Test schema loading from directory."""
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    
    # Create test schema files
    valid_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        }
    }
    
    # Only create valid schema initially
    with open(schema_dir / "valid.json", "w") as f:
        json.dump(valid_schema, f)
    
    service = ConfigSchemaService(service_name="schema", schema_dir=schema_dir)
    await service._start()
    
    # Valid schema should be loaded
    assert "valid" in service._schemas
    assert service._schemas["valid"].type == "object"
    
    # Now test invalid schema
    invalid_schema = "not a schema"
    with open(schema_dir / "invalid.json", "w") as f:
        f.write(invalid_schema)
    
    # Reload schemas should fail
    with pytest.raises(ConfigError) as exc_info:
        await service._load_schemas()
    assert "Failed to load schemas" in str(exc_info.value)


@pytest.mark.asyncio
async def test_array_validation(schema_service):
    """Test validation of array types."""
    array_schema = {
        "type": "object",
        "properties": {
            "numbers": {
                "type": "array",
                "items": {
                    "type": "number",
                    "min_value": 0,
                    "max_value": 100
                }
            },
            "strings": {
                "type": "array",
                "items": {
                    "type": "string",
                    "pattern": r"^[A-Z][a-z]+$"
                }
            }
        }
    }
    schema_service._schemas["array"] = ConfigSchema(**array_schema)
    
    # Valid arrays
    valid_config = {
        "numbers": [0, 50, 100],
        "strings": ["Hello", "World"]
    }
    errors = schema_service.validate_config("array", valid_config)
    assert len(errors) == 0
    
    # Invalid array items
    invalid_config = {
        "numbers": [-1, 101, "not a number"],
        "strings": ["invalid", "Invalid", 123]
    }
    errors = schema_service.validate_config("array", invalid_config)
    assert len(errors) == 5  # Updated expected error count
    assert any("Value must be >= 0" in error for error in errors)
    assert any("Value must be <= 100" in error for error in errors)
    assert any("Expected number" in error for error in errors)
    assert any("String does not match pattern" in error for error in errors)
    assert any("Expected string" in error for error in errors)


@pytest.mark.asyncio
async def test_nested_object_validation(schema_service):
    """Test validation of deeply nested objects."""
    nested_schema = {
        "type": "object",
        "properties": {
            "level1": {
                "type": "object",
                "properties": {
                    "level2": {
                        "type": "object",
                        "properties": {
                            "level3": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"}
                                },
                                "required": ["value"]
                            }
                        }
                    }
                }
            }
        }
    }
    schema_service._schemas["nested"] = ConfigSchema(**nested_schema)
    
    # Valid nested object
    valid_config = {
        "level1": {
            "level2": {
                "level3": {
                    "value": 42
                }
            }
        }
    }
    errors = schema_service.validate_config("nested", valid_config)
    assert len(errors) == 0
    
    # Missing required field
    invalid_config = {
        "level1": {
            "level2": {
                "level3": {}
            }
        }
    }
    errors = schema_service.validate_config("nested", invalid_config)
    assert len(errors) == 1
    assert "Missing required field" in errors[0]
    
    # Invalid type at deep level
    invalid_type_config = {
        "level1": {
            "level2": {
                "level3": {
                    "value": "not a number"
                }
            }
        }
    }
    errors = schema_service.validate_config("nested", invalid_type_config)
    assert len(errors) == 1
    assert "Expected number" in errors[0]


@pytest.mark.asyncio
async def test_error_handling(schema_service):
    """Test error handling for various edge cases."""
    # Test with non-existent schema
    with pytest.raises(ConfigError) as exc_info:
        schema_service.validate_config("non_existent", {})
    assert "Schema not found" in str(exc_info.value)
    
    # Test with None values
    schema = {
        "type": "object",
        "properties": {
            "nullable": {"type": "string"}
        }
    }
    schema_service._schemas["nullable"] = ConfigSchema(**schema)
    
    config = {"nullable": None}
    errors = schema_service.validate_config("nullable", config)
    assert len(errors) == 1
    assert "Expected string" in errors[0]
    
    # Test with empty objects/arrays
    empty_schema = {
        "type": "object",
        "properties": {
            "empty_obj": {"type": "object"},
            "empty_arr": {"type": "array"}
        }
    }
    schema_service._schemas["empty"] = ConfigSchema(**empty_schema)
    
    empty_config = {
        "empty_obj": {},
        "empty_arr": []
    }
    errors = schema_service.validate_config("empty", empty_config)
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_edge_cases(schema_service):
    """Test various edge cases and special values."""
    edge_schema = {
        "type": "object",
        "properties": {
            "zero": {"type": "number"},
            "empty_string": {"type": "string"},
            "bool_value": {"type": "boolean"},
            "special_chars": {
                "type": "string",
                "pattern": r"^[!@#$%^&*()]+$"
            }
        }
    }
    schema_service._schemas["edge"] = ConfigSchema(**edge_schema)
    
    # Test edge values
    edge_config = {
        "zero": 0,
        "empty_string": "",
        "bool_value": False,
        "special_chars": "!@#$%^&*()"
    }
    errors = schema_service.validate_config("edge", edge_config)
    assert len(errors) == 0
    
    # Test with very large numbers
    large_number_config = {
        "zero": 1e308  # Max float value
    }
    errors = schema_service.validate_config("edge", large_number_config)
    assert len(errors) == 0
    
    # Test with very long strings
    long_string_config = {
        "empty_string": "a" * 1000000
    }
    errors = schema_service.validate_config("edge", long_string_config)
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_schema_building(schema_service):
    """Test schema building from raw data."""
    # Test building valid schema
    valid_schema_data = {
        "type": "object",
        "properties": {
            "test": {"type": "string"}
        }
    }
    schema = schema_service.build_schema(valid_schema_data)
    assert schema.type == "object"
    assert "test" in schema.properties
    
    # Test building invalid schema
    invalid_schema_data = {
        "type": "invalid_type",
        "properties": {}
    }
    with pytest.raises(ValueError):
        schema_service.build_schema(invalid_schema_data)
