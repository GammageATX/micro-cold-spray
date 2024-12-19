"""Tests for format service."""

import pytest
from unittest.mock import patch, MagicMock
from loguru import logger

from micro_cold_spray.api.config.services.config_format_service import ConfigFormatService
from micro_cold_spray.api.base.base_exceptions import ConfigError, ValidationError
from micro_cold_spray.api.config.models import FormatMetadata


@pytest.fixture(autouse=True)
def reset_format_service():
    """Reset format service singleton between tests."""
    ConfigFormatService._instance = None
    ConfigFormatService._initialized = False
    yield


@pytest.fixture
def format_service():
    """Create format service."""
    service = ConfigFormatService(service_name="format")
    return service


@pytest.mark.asyncio
async def test_service_start(format_service):
    """Test service startup."""
    await format_service.start()
    assert format_service.is_running
    assert len(format_service._format_validators) > 0  # Default validators should be registered


@pytest.mark.asyncio
async def test_service_start_error():
    """Test service startup with error."""
    service = ConfigFormatService(service_name="format")
    
    # Mock logger.info to raise error
    with patch.object(logger, 'info', side_effect=Exception("Start error")):
        with pytest.raises(ConfigError, match="Failed to start format service"):
            await service.start()


def test_singleton():
    """Test format service singleton pattern."""
    service1 = ConfigFormatService(service_name="format")
    service2 = ConfigFormatService(service_name="format")
    assert service1 is service2
    assert service1._initialized == service2._initialized


@pytest.mark.asyncio
async def test_register_format(format_service):
    """Test registering new format validator."""
    await format_service.start()
    
    def validator(value):
        return None if value > 0 else "Value must be positive"
    
    format_service.register_format(
        "positive",
        validator,
        "Validates positive numbers",
        ["1", "42", "3.14"]
    )
    
    assert "positive" in format_service._format_validators
    assert "positive" in format_service._format_metadata
    
    metadata = format_service._format_metadata["positive"]
    assert metadata.description == "Validates positive numbers"
    assert metadata.examples == ["1", "42", "3.14"]
    
    # Test the registered validator
    assert format_service.validate_format("positive", 42) is None
    with pytest.raises(ValidationError, match="Format validation failed"):
        format_service.validate_format("positive", -1)


@pytest.mark.asyncio
async def test_register_format_duplicate(format_service):
    """Test registering duplicate format."""
    await format_service.start()
    
    def validator(value):
        return None
    
    format_service.register_format(
        "test",
        validator,
        "Test format",
        ["example"]
    )
    
    with pytest.raises(ConfigError) as exc_info:
        format_service.register_format(
            "test",
            validator,
            "Test format",
            ["example"]
        )
    assert "Format already registered" in str(exc_info.value)


@pytest.mark.asyncio
async def test_register_format_error(format_service):
    """Test registering format with error."""
    await format_service.start()
    
    with patch('micro_cold_spray.api.config.services.format_service.FormatMetadata') as mock_metadata:
        mock_metadata.side_effect = Exception("Metadata error")
        with pytest.raises(ConfigError) as exc_info:
            format_service.register_format(
                "test",
                lambda x: None,
                "Test format",
                ["example"]
            )
        assert "Failed to register format" in str(exc_info.value)


def test_validate_format_unknown(format_service):
    """Test validating unknown format."""
    with pytest.raises(ValidationError, match="Unknown format type") as exc_info:
        format_service.validate_format("unknown", "value")
    assert "available_formats" in exc_info.value.context


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
    
    with pytest.raises(ValidationError, match="Format validation failed") as exc_info:
        format_service.validate_format("error", "value")
    assert "error" in exc_info.value.context


def test_validate_12bit(format_service):
    """Test 12-bit value validation."""
    # Valid values
    assert format_service._validate_12bit(0) is None
    assert format_service._validate_12bit(2048) is None
    assert format_service._validate_12bit(4095) is None
    assert format_service._validate_12bit(1234.5) is None
    
    # Invalid values
    assert "must be between 0 and 4095" in format_service._validate_12bit(-1)
    assert "must be between 0 and 4095" in format_service._validate_12bit(4096)
    assert "must be numeric" in format_service._validate_12bit("not a number")
    assert "must be numeric" in format_service._validate_12bit(None)
    
    # Test error handling
    with patch('builtins.float', side_effect=Exception("Conversion error")):
        error = format_service._validate_12bit(123)
        assert "Validation failed" in error


def test_validate_percentage(format_service):
    """Test percentage value validation."""
    # Valid values
    assert format_service._validate_percentage(0) is None
    assert format_service._validate_percentage(50) is None
    assert format_service._validate_percentage(100) is None
    assert format_service._validate_percentage(75.5) is None
    
    # Invalid values
    assert "must be between 0 and 100" in format_service._validate_percentage(-1)
    assert "must be between 0 and 100" in format_service._validate_percentage(101)
    assert "must be numeric" in format_service._validate_percentage("not a number")
    assert "must be numeric" in format_service._validate_percentage(None)
    
    # Test error handling
    with patch('builtins.float', side_effect=Exception("Conversion error")):
        error = format_service._validate_percentage(123)
        assert "Validation failed" in error


def test_validate_ip_address(format_service):
    """Test IP address validation."""
    # Valid values
    assert format_service._validate_ip_address("192.168.1.1") is None
    assert format_service._validate_ip_address("10.0.0.0") is None
    assert format_service._validate_ip_address("255.255.255.255") is None
    
    # Invalid values
    assert "must be string" in format_service._validate_ip_address(123)
    assert "Invalid IP address format" in format_service._validate_ip_address("1.2.3")
    assert "Invalid IP address format" in format_service._validate_ip_address("not.an.ip.address")
    assert "must be between 0 and 255" in format_service._validate_ip_address("256.1.2.3")
    assert "must be between 0 and 255" in format_service._validate_ip_address("1.2.3.256")
    
    # Test error handling
    with patch('re.match', side_effect=Exception("Regex error")):
        error = format_service._validate_ip_address("192.168.1.1")
        assert "Invalid IP address format" in error


def test_validate_hostname(format_service):
    """Test hostname validation."""
    # Valid values
    assert format_service._validate_hostname("localhost") is None
    assert format_service._validate_hostname("example.com") is None
    assert format_service._validate_hostname("sub-domain.example.com") is None
    assert format_service._validate_hostname("a" * 63) is None  # Single label hostname

    # Invalid values
    assert "must be string" in format_service._validate_hostname(123)
    assert "Invalid hostname format" in format_service._validate_hostname("-invalid.com")
    assert "Invalid hostname format" in format_service._validate_hostname("invalid-.com")
    assert "Invalid hostname format" in format_service._validate_hostname("inv@lid.com")
    assert "Hostname too long" in format_service._validate_hostname("a" * 256)
    assert "Label too long" in format_service._validate_hostname("a" * 64 + ".com")

    # Test error handling
    class MockStr(str):
        def __len__(self):
            raise Exception("Validation error")
    error = format_service._validate_hostname(MockStr("example.com"))
    assert "Validation failed: Validation error" in error


def test_validate_port(format_service):
    """Test port number validation."""
    # Valid values
    assert format_service._validate_port(1) is None
    assert format_service._validate_port(8080) is None
    assert format_service._validate_port(65535) is None
    
    # Invalid values
    assert "Port must be integer" in format_service._validate_port(1.5)
    assert "Port must be integer" in format_service._validate_port("80")
    assert "Port must be between 1 and 65535" in format_service._validate_port(0)
    assert "Port must be between 1 and 65535" in format_service._validate_port(65536)
    
    # Test error handling
    def mock_isinstance(*args, **kwargs):
        raise Exception("Type check error")
    
    with patch('builtins.isinstance', mock_isinstance):
        error = format_service._validate_port(8080)
        assert "Validation failed: Type check error" in error


def test_validate_path(format_service):
    """Test path validation."""
    # Valid values
    assert format_service._validate_path("/absolute/path") is None
    assert format_service._validate_path("relative/path") is None
    assert format_service._validate_path("C:\\Windows\\System32") is None
    assert format_service._validate_path("path/with spaces") is None

    # Invalid values
    assert "must be string" in format_service._validate_path(123)
    assert "Path cannot be empty" in format_service._validate_path("")
    assert "Path cannot be empty" in format_service._validate_path("   ")
    assert "invalid characters" in format_service._validate_path("path/with/invalid/chars/<>|?*")
    assert "Path too long" in format_service._validate_path("a" * 261)
    assert "parent directory references" in format_service._validate_path("../parent/path")

    # Test error handling
    with patch('micro_cold_spray.api.config.services.format_service.Path', side_effect=Exception("Path error")):
        error = format_service._validate_path("/some/path")
        assert "Invalid path format: Path error" in error


def test_validate_tag_path(format_service):
    """Test tag path validation."""
    # Valid values
    assert format_service._validate_tag_path("tag") is None
    assert format_service._validate_tag_path("group.tag") is None
    assert format_service._validate_tag_path("group.subgroup.tag") is None
    assert format_service._validate_tag_path("Tag_123.Sub_456.tag_789") is None
    
    # Invalid values
    assert "must be string" in format_service._validate_tag_path(123)
    assert "Invalid tag path format" in format_service._validate_tag_path("")
    assert "Invalid tag path format" in format_service._validate_tag_path("123tag")
    assert "Invalid tag path format" in format_service._validate_tag_path("tag.")
    assert "Invalid tag path format" in format_service._validate_tag_path(".tag")
    assert "Invalid tag path format" in format_service._validate_tag_path("tag..tag")
    assert "Invalid tag path format" in format_service._validate_tag_path("tag@group")
    assert "Tag path too long" in format_service._validate_tag_path("a" * 256)
    
    # Test error handling
    mock_match = MagicMock(side_effect=Exception("Regex error"))
    with patch('re.match', mock_match):
        error = format_service._validate_tag_path("group.tag")
        assert "Invalid tag path format: Regex error" in error


def test_validate_format_integration(format_service):
    """Test format validation integration with all default formats."""
    # Test all default formats with valid values
    test_cases = [
        ("12bit", 2048),
        ("percentage", 75),
        ("ip_address", "192.168.1.1"),
        ("hostname", "example.com"),
        ("port", 8080),
        ("path", "/valid/path"),
        ("tag_path", "group.tag")
    ]
    
    for format_type, value in test_cases:
        assert format_service.validate_format(format_type, value) is None
        
    # Test validation error propagation
    invalid_test_cases = [
        ("12bit", "invalid"),
        ("percentage", "invalid"),
        ("ip_address", "invalid"),
        ("hostname", "invalid@host"),
        ("port", "invalid"),
        ("path", "<invalid>"),
        ("tag_path", "invalid..")
    ]
    
    for format_type, value in invalid_test_cases:
        with pytest.raises(ValidationError, match="Format validation failed"):
            format_service.validate_format(format_type, value)


def test_default_validators_registration():
    """Test that default validators are properly registered."""
    service = ConfigFormatService()
    
    expected_formats = {
        "12bit",
        "percentage",
        "ip_address",
        "hostname",
        "port",
        "path",
        "tag_path"
    }
    
    assert set(service._format_validators.keys()) == expected_formats
    assert set(service._format_metadata.keys()) == expected_formats
    
    # Verify each format has proper metadata
    for format_type in expected_formats:
        metadata = service._format_metadata[format_type]
        assert isinstance(metadata, FormatMetadata)
        assert metadata.description
        assert isinstance(metadata.examples, list)
        assert len(metadata.examples) > 0
