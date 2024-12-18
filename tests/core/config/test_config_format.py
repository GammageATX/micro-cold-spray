"""Tests for format service."""

import pytest
from fastapi import status, HTTPException
from loguru import logger
from unittest.mock import patch

from micro_cold_spray.api.config.services.format_service import FormatService


@pytest.fixture(autouse=True)
def reset_format_service():
    """Reset format service singleton between tests."""
    FormatService._instance = None
    FormatService._initialized = False
    yield


@pytest.fixture
def format_service():
    """Create format service."""
    service = FormatService()
    return service


@pytest.fixture
def test_validator():
    """Create test validator function."""
    def validator(value):
        return None if value > 0 else "Value must be positive"
    return validator


@pytest.fixture
def test_format_metadata():
    """Create test format metadata."""
    return {
        "name": "positive",
        "description": "Validates positive numbers",
        "examples": ["1", "42", "3.14"]
    }


@pytest.mark.asyncio
async def test_service_start(format_service):
    """Test service startup."""
    await format_service.start()
    assert format_service.is_running
    assert len(format_service._format_validators) > 0  # Default validators should be registered
    
    # Check health
    health = await format_service._check_health()
    assert health["validators"] > 0
    assert len(health["formats"]) > 0


@pytest.mark.asyncio
async def test_service_start_error():
    """Test service startup with error."""
    service = FormatService()
    
    # Mock logger.info to raise error
    with patch.object(logger, 'info', side_effect=Exception("Start error")):
        with pytest.raises(HTTPException) as exc_info:
            await service.start()
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Start error" in str(exc_info.value.detail)


def test_singleton():
    """Test format service singleton pattern."""
    service1 = FormatService()
    service2 = FormatService()
    assert service1 is service2
    assert service1._initialized == service2._initialized


@pytest.mark.asyncio
async def test_register_format(format_service, test_validator, test_format_metadata):
    """Test registering new format validator."""
    await format_service.start()
    
    format_service.register_format(
        test_format_metadata["name"],
        test_validator,
        test_format_metadata["description"],
        test_format_metadata["examples"]
    )
    
    assert test_format_metadata["name"] in format_service._format_validators
    assert test_format_metadata["name"] in format_service._format_metadata
    
    metadata = format_service._format_metadata[test_format_metadata["name"]]
    assert metadata.description == test_format_metadata["description"]
    assert metadata.examples == test_format_metadata["examples"]
    
    # Test the registered validator
    assert format_service.validate_format(test_format_metadata["name"], 42) is None
    with pytest.raises(HTTPException) as exc_info:
        format_service.validate_format(test_format_metadata["name"], -1)
    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Value must be positive" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_register_format_duplicate(format_service, test_validator, test_format_metadata):
    """Test registering duplicate format."""
    await format_service.start()
    
    format_service.register_format(
        test_format_metadata["name"],
        test_validator,
        test_format_metadata["description"],
        test_format_metadata["examples"]
    )
    
    with pytest.raises(HTTPException) as exc_info:
        format_service.register_format(
            test_format_metadata["name"],
            test_validator,
            test_format_metadata["description"],
            test_format_metadata["examples"]
        )
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "already registered" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_register_format_error(format_service, test_validator, test_format_metadata):
    """Test registering format with error."""
    await format_service.start()
    
    with patch('micro_cold_spray.api.config.services.format_service.FormatMetadata') as mock_metadata:
        mock_metadata.side_effect = Exception("Metadata error")
        with pytest.raises(HTTPException) as exc_info:
            format_service.register_format(
                test_format_metadata["name"],
                test_validator,
                test_format_metadata["description"],
                test_format_metadata["examples"]
            )
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to register format" in str(exc_info.value.detail)


def test_validate_format_unknown(format_service):
    """Test validating unknown format."""
    with pytest.raises(HTTPException) as exc_info:
        format_service.validate_format("unknown", "value")
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Unknown format type" in str(exc_info.value.detail)
    assert "available_formats" in exc_info.value.detail


def test_validate_format_error(format_service):
    """Test validation with unexpected error."""
    def validator(value):
        raise Exception("Unexpected error")
    
    format_service.register_format(
        "error",
        validator,
        "Error format",
        ["example"]
    )
    
    with pytest.raises(HTTPException) as exc_info:
        format_service.validate_format("error", "value")
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Format validation failed" in str(exc_info.value.detail)


@pytest.mark.parametrize("value,expected_error", [
    (0, None),
    (2048, None),
    (4095, None),
    (1234.5, None),
    (-1, "must be between 0 and 4095"),
    (4096, "must be between 0 and 4095"),
    ("not a number", "must be numeric"),
    (None, "must be numeric")
])
def test_validate_12bit(format_service, value, expected_error):
    """Test 12-bit value validation."""
    result = format_service._validate_12bit(value)
    if expected_error:
        assert expected_error in result
    else:
        assert result is None
    
    # Test error handling
    with patch('builtins.float', side_effect=Exception("Conversion error")):
        error = format_service._validate_12bit(123)
        assert "Validation failed" in error


@pytest.mark.parametrize("value,expected_error", [
    (0, None),
    (50, None),
    (100, None),
    (75.5, None),
    (-1, "must be between 0 and 100"),
    (101, "must be between 0 and 100"),
    ("not a number", "must be numeric"),
    (None, "must be numeric")
])
def test_validate_percentage(format_service, value, expected_error):
    """Test percentage value validation."""
    result = format_service._validate_percentage(value)
    if expected_error:
        assert expected_error in result
    else:
        assert result is None
    
    # Test error handling
    with patch('builtins.float', side_effect=Exception("Conversion error")):
        error = format_service._validate_percentage(123)
        assert "Validation failed" in error


@pytest.mark.parametrize("value,expected_error", [
    ("192.168.1.1", None),
    ("10.0.0.0", None),
    ("255.255.255.255", None),
    (123, "must be string"),
    ("1.2.3", "Invalid IP address format"),
    ("not.an.ip.address", "Invalid IP address format"),
    ("256.1.2.3", "must be between 0 and 255"),
    ("1.2.3.256", "must be between 0 and 255")
])
def test_validate_ip_address(format_service, value, expected_error):
    """Test IP address validation."""
    result = format_service._validate_ip_address(value)
    if expected_error:
        assert expected_error in result
    else:
        assert result is None
    
    # Test error handling
    with patch('re.match', side_effect=Exception("Regex error")):
        error = format_service._validate_ip_address("192.168.1.1")
        assert "Invalid IP address format" in error


@pytest.mark.parametrize("value,expected_error", [
    ("localhost", None),
    ("example.com", None),
    ("sub-domain.example.com", None),
    ("a" * 63, None),
    (123, "must be string"),
    ("-invalid.com", "Invalid hostname format"),
    ("invalid-.com", "Invalid hostname format"),
    ("inv@lid.com", "Invalid hostname format"),
    ("a" * 256, "Hostname too long"),
    ("a" * 64 + ".com", "Label too long")
])
def test_validate_hostname(format_service, value, expected_error):
    """Test hostname validation."""
    result = format_service._validate_hostname(value)
    if expected_error:
        assert expected_error in result
    else:
        assert result is None
    
    # Test error handling
    class MockStr(str):
        def __len__(self):
            raise Exception("Validation error")
    error = format_service._validate_hostname(MockStr("example.com"))
    assert "Validation failed: Validation error" in error


@pytest.mark.parametrize("value,expected_error", [
    (1, None),
    (8080, None),
    (65535, None),
    (0, "must be between 1 and 65535"),
    (65536, "must be between 1 and 65535"),
    ("not a number", "must be numeric"),
    (None, "must be numeric")
])
def test_validate_port(format_service, value, expected_error):
    """Test port number validation."""
    result = format_service._validate_port(value)
    if expected_error:
        assert expected_error in result
    else:
        assert result is None
    
    # Test error handling
    with patch('builtins.int', side_effect=Exception("Conversion error")):
        error = format_service._validate_port(123)
        assert "Validation failed" in error
