"""Tests for validation service."""

import pytest
from unittest.mock import AsyncMock

from micro_cold_spray.api.validation.service import ValidationService
from micro_cold_spray.api.validation.exceptions import ValidationError
from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.messaging import MessagingService


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    service = AsyncMock(spec=ConfigService)
    service.get_config.return_value = {
        "process": {
            "validation": {
                "parameters": {
                    "required_fields": ["speed", "pressure"],
                    "bounds": {
                        "speed": [0, 100],
                        "pressure": [0, 50]
                    }
                },
                "sequences": {
                    "required_fields": {
                        "fields": ["name", "type", "steps"]
                    },
                    "max_steps": 10
                },
                "patterns": {
                    "types": ["zigzag", "linear"],
                    "bounds": {
                        "width": [0, 1000],
                        "height": [0, 1000]
                    }
                }
            }
        }
    }
    return service


@pytest.fixture
def mock_message_broker():
    """Create mock message broker."""
    return AsyncMock(spec=MessagingService)


@pytest.fixture
async def validation_service(mock_config_service, mock_message_broker):
    """Create validation service instance."""
    service = ValidationService(mock_config_service, mock_message_broker)
    await service.start()
    return service


class TestValidationService:
    """Test validation service functionality."""

    async def test_initialization(self, validation_service, mock_config_service, mock_message_broker):
        """Test service initialization."""
        assert validation_service._config_service == mock_config_service
        assert validation_service._message_broker == mock_message_broker
        assert validation_service._validation_rules is not None
        assert validation_service._pattern_validator is not None
        assert validation_service._sequence_validator is not None
        assert validation_service._hardware_validator is not None
        assert validation_service._parameter_validator is not None

    async def test_start_success(self, mock_config_service, mock_message_broker):
        """Test successful service start."""
        service = ValidationService(mock_config_service, mock_message_broker)
        await service.start()
        
        assert service.is_running
        mock_config_service.get_config.assert_called_once_with("process")
        mock_message_broker.subscribe.assert_called_once_with(
            "validation/request",
            service._handle_validation_request
        )

    async def test_start_config_error(self, mock_config_service, mock_message_broker):
        """Test service start with config error."""
        mock_config_service.get_config.side_effect = Exception("Config error")
        service = ValidationService(mock_config_service, mock_message_broker)
        
        with pytest.raises(ValidationError) as exc_info:
            await service.start()
        assert "Failed to start validation service" in str(exc_info.value)
        assert not service.is_running

    async def test_validate_parameters_success(self, validation_service):
        """Test successful parameter validation."""
        data = {
            "speed": 50,
            "pressure": 25
        }
        result = await validation_service.validate_parameters(data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    async def test_validate_pattern_success(self, validation_service):
        """Test successful pattern validation."""
        data = {
            "type": "zigzag",
            "width": 500,
            "height": 500
        }
        result = await validation_service.validate_pattern(data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    async def test_validate_sequence_success(self, validation_service):
        """Test successful sequence validation."""
        data = {
            "name": "Test Sequence",
            "type": "spray",
            "steps": [
                {
                    "name": "Start",
                    "action": "start",
                    "parameters": {
                        "speed": 50,
                        "pressure": 25
                    }
                }
            ]
        }
        result = await validation_service.validate_sequence(data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    async def test_validate_hardware_success(self, validation_service):
        """Test successful hardware validation."""
        data = {
            "feeder": True,
            "motion": True
        }
        result = await validation_service.validate_hardware(data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    async def test_get_rules_success(self, validation_service):
        """Test successful rules retrieval."""
        rules = await validation_service.get_rules("parameters")
        
        assert rules is not None
        assert "required_fields" in rules
        assert "bounds" in rules

    async def test_get_rules_unknown_type(self, validation_service):
        """Test rules retrieval for unknown type."""
        with pytest.raises(ValidationError) as exc_info:
            await validation_service.get_rules("unknown")
        assert "Unknown rule type" in str(exc_info.value)

    async def test_handle_validation_request_success(self, validation_service, mock_message_broker):
        """Test successful validation request handling."""
        request = {
            "type": "parameters",
            "data": {
                "speed": 50,
                "pressure": 25
            },
            "request_id": "test-123"
        }
        
        await validation_service._handle_validation_request(request)
        
        mock_message_broker.publish.assert_called_once()
        response = mock_message_broker.publish.call_args[0][1]
        assert response["request_id"] == "test-123"
        assert response["valid"] is True
        assert "timestamp" in response

    async def test_handle_validation_request_error(self, validation_service, mock_message_broker):
        """Test validation request handling with error."""
        request = {
            "type": "unknown",
            "data": {},
            "request_id": "test-123"
        }
        
        await validation_service._handle_validation_request(request)
        
        mock_message_broker.publish.assert_called_once()
        response = mock_message_broker.publish.call_args[0][1]
        assert response["request_id"] == "test-123"
        assert response["valid"] is False
        assert len(response["errors"]) > 0
        assert "timestamp" in response

    async def test_handle_validation_request_missing_type(self, validation_service, mock_message_broker):
        """Test validation request handling with missing type."""
        request = {
            "data": {},
            "request_id": "test-123"
        }
        
        await validation_service._handle_validation_request(request)
        
        mock_message_broker.publish.assert_called_once()
        response = mock_message_broker.publish.call_args[0][1]
        assert response["request_id"] == "test-123"
        assert response["valid"] is False
        assert any("type" in error.lower() for error in response["errors"])

    async def test_handle_validation_request_missing_data(self, validation_service, mock_message_broker):
        """Test validation request handling with missing data."""
        request = {
            "type": "parameters",
            "request_id": "test-123"
        }
        
        await validation_service._handle_validation_request(request)
        
        mock_message_broker.publish.assert_called_once()
        response = mock_message_broker.publish.call_args[0][1]
        assert response["request_id"] == "test-123"
        assert response["valid"] is False
        assert any("data" in error.lower() for error in response["errors"])
