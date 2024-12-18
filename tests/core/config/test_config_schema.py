"""Tests for schema service."""

import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi import status, HTTPException

from micro_cold_spray.api.config.services.schema_service import SchemaService
from micro_cold_spray.api.config.models import ConfigSchema
from tests.utils import assert_error_response, assert_service_response
from .helpers import create_test_schema


@pytest.fixture
def schema_dir(tmp_path):
    """Create temporary schema directory."""
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    return schema_dir


@pytest.fixture
def schema_service(schema_dir):
    """Create schema service instance."""
    return SchemaService(schema_dir)


@pytest.fixture
def sample_schema(test_config):
    """Create sample schema data using common test config."""
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
    
    # Check health using common assertion
    health = await schema_service._check_health()
    assert_service_response(health)
    assert health["schemas"] == 0  # Empty at start
    assert isinstance(health["schema_types"], list)


@pytest.mark.asyncio
async def test_service_start_error():
    """Test service startup with error."""
    # Mock _load_schemas to raise an error
    service = SchemaService(Path("/tmp/schemas"))
    with patch.object(service, '_load_schemas', side_effect=Exception("Load error")):
        with pytest.raises(HTTPException) as exc_info:
            await service.start()
        assert_error_response(
            exc_info,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Failed to start schema service"
        )


@pytest.mark.asyncio
async def test_load_schemas(schema_dir, sample_schema):
    """Test loading schemas from files."""
    # Create a test schema file
    create_test_schema(schema_dir, "test", sample_schema)

    service = SchemaService(schema_dir)
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
    create_test_schema(schema_dir, "invalid", ["invalid"])

    service = SchemaService(schema_dir)
    with pytest.raises(HTTPException) as exc_info:
        await service.start()
    assert_error_response(
        exc_info,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Invalid schema format"
    )


@pytest.mark.asyncio
async def test_load_schemas_invalid_json(schema_dir):
    """Test loading invalid JSON file."""
    # Create invalid JSON file
    schema_file = schema_dir / "invalid.json"
    with open(schema_file, "w") as f:
        f.write("invalid json")

    service = SchemaService(schema_dir)
    with pytest.raises(HTTPException) as exc_info:
        await service.start()
    assert_error_response(
        exc_info,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Failed to load schemas"
    )


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
    with pytest.raises(HTTPException) as exc_info:
        schema_service.build_schema({"invalid": "schema"})
    assert_error_response(
        exc_info,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Invalid schema format"
    )


@pytest.mark.asyncio
async def test_validate_config(schema_service, sample_schema, test_config):
    """Test configuration validation using common test config."""
    schema_service._schemas["test"] = ConfigSchema(**sample_schema)
    
    # Valid config
    errors = schema_service.validate_config("test", test_config)
    assert len(errors) == 0
    
    # Invalid config - missing required field
    invalid_config = {"name": "test"}
    errors = schema_service.validate_config("test", invalid_config)
    assert len(errors) > 0
    assert any("value" in error for error in errors)


@pytest.mark.asyncio
async def test_validate_config_schema_not_found():
    """Test validation when schema registry is not initialized."""
    service = SchemaService(Path("/tmp/schemas"))
    await service.start()
    
    with pytest.raises(HTTPException) as exc_info:
        await service.validate_config("nonexistent", {})
    assert_error_response(
        exc_info,
        status.HTTP_404_NOT_FOUND,
        "Schema not found"
    )


@pytest.mark.asyncio
async def test_validate_config_unexpected_error(schema_service, sample_schema):
    """Test validation with unexpected error."""
    schema_service._schemas["test"] = ConfigSchema(**sample_schema)
    
    # Mock _validate_against_schema to raise unexpected error
    with patch.object(schema_service, '_validate_against_schema', side_effect=Exception("Unexpected")):
        with pytest.raises(HTTPException) as exc_info:
            schema_service.validate_config("test", {})
        assert_error_response(
            exc_info,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Validation failed"
        )


@pytest.mark.parametrize("schema_type,config_data,expected_errors", [
    ("test", {"name": "test", "value": 42}, 0),  # Valid config
    ("test", {"name": "test"}, 1),  # Missing required field
    ("test", {"name": "test", "value": "not a number"}, 1),  # Wrong type
    ("test", {"name": 123, "value": "wrong"}, 2),  # Multiple errors
])
def test_validate_config_parametrized(schema_service, sample_schema, schema_type, config_data, expected_errors):
    """Test configuration validation with different test cases."""
    schema_service._schemas[schema_type] = ConfigSchema(**sample_schema)
    errors = schema_service.validate_config(schema_type, config_data)
    assert len(errors) == expected_errors


@pytest.mark.asyncio
async def test_schema_loading_validation(schema_service, valid_schema, tmp_path):
    """Test schema loading with validation."""
    create_test_schema(tmp_path / "schemas", "test", valid_schema)
    await schema_service.start()
    
    loaded_schema = schema_service.get_schema("test")
    assert loaded_schema is not None
    assert loaded_schema.type == "object"
    assert loaded_schema.title == "Test Schema"
    assert loaded_schema.required == ["field1"]


@pytest.mark.asyncio
async def test_schema_loading_invalid_json(schema_service, tmp_path):
    """Test schema loading with invalid JSON."""
    schema_file = tmp_path / "schemas" / "invalid.json"
    schema_file.write_text("{invalid json")
    
    with pytest.raises(HTTPException) as exc_info:
        await schema_service._load_schemas()
    assert_error_response(
        exc_info,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Failed to load schemas"
    )


@pytest.mark.asyncio
async def test_schema_loading_invalid_schema(schema_service, invalid_schema, tmp_path):
    """Test schema loading with invalid schema structure."""
    create_test_schema(tmp_path / "schemas", "invalid", invalid_schema)
    
    with pytest.raises(HTTPException) as exc_info:
        await schema_service._load_schemas()
    assert_error_response(
        exc_info,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Schema validation failed"
    )


@pytest.mark.asyncio
async def test_schema_loading_non_dict(schema_service, tmp_path):
    """Test schema loading with non-dictionary data."""
    create_test_schema(tmp_path / "schemas", "invalid", ["not", "a", "dict"])
    
    with pytest.raises(HTTPException) as exc_info:
        await schema_service._load_schemas()
    assert_error_response(
        exc_info,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Invalid schema format"
    )
