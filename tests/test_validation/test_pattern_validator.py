"""Tests for pattern validator."""

import pytest
from unittest.mock import AsyncMock
from typing import Dict, Any

from micro_cold_spray.api.validation.validators.pattern_validator import (
    PatternValidator
)
from micro_cold_spray.api.validation.exceptions import ValidationError
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.config import ConfigService


@pytest.fixture
def validation_rules() -> Dict[str, Any]:
    """Create test validation rules."""
    return {
        "patterns": {
            "limits": {
                "position": {
                    "message": "Pattern exceeds stage limits"
                },
                "speed": {
                    "message": "Speed exceeds maximum allowed"
                }
            },
            "serpentine": {
                "required_fields": {
                    "fields": ["length", "spacing"]
                },
                "optional_fields": {
                    "fields": ["speed", "offset"]
                }
            },
            "spiral": {
                "required_fields": {
                    "fields": ["diameter", "pitch"]
                },
                "optional_fields": {
                    "fields": ["speed", "revolutions"]
                }
            }
        }
    }


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    config = AsyncMock(spec=ConfigService)
    config.get_config.return_value = {
        "hardware": {
            "physical": {
                "stage": {
                    "dimensions": {
                        "x": 1000.0,
                        "y": 1000.0,
                        "z": 500.0
                    }
                }
            },
            "safety": {
                "motion": {
                    "max_speed": 100.0
                }
            }
        }
    }
    return config


@pytest.fixture
def mock_message_broker():
    """Create mock message broker."""
    return AsyncMock(spec=MessagingService)


@pytest.fixture
def validator(validation_rules, mock_config_service, mock_message_broker):
    """Create pattern validator instance."""
    return PatternValidator(validation_rules, mock_config_service, mock_message_broker)


class TestPatternValidator:
    """Test pattern validator functionality."""

    async def test_initialization(self, validator, validation_rules, mock_config_service):
        """Test validator initialization."""
        assert validator._rules == validation_rules
        assert validator._config_service == mock_config_service
        assert validator._message_broker is not None

    async def test_validate_missing_type(self, validator):
        """Test validation with missing pattern type."""
        result = await validator.validate({})
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "Pattern type not specified" in result["errors"][0]

    async def test_validate_unknown_type(self, validator):
        """Test validation with unknown pattern type."""
        result = await validator.validate({"type": "unknown"})
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "Unknown pattern type" in result["errors"][0]

    async def test_validate_pattern_bounds_success(self, validator):
        """Test successful pattern bounds validation."""
        pattern = {
            "type": "serpentine",
            "params": {
                "length": 500.0,
                "spacing": 10.0
            },
            "position": {
                "x": 100.0,
                "y": 100.0,
                "z": 100.0
            }
        }
        errors = await validator._validate_pattern_bounds(
            pattern,
            validator._rules["patterns"]["limits"]
        )
        assert len(errors) == 0

    async def test_validate_pattern_bounds_exceed_limits(self, validator):
        """Test pattern bounds exceeding stage limits."""
        pattern = {
            "type": "serpentine",
            "params": {
                "length": 2000.0,  # Exceeds stage limits
                "spacing": 10.0
            },
            "position": {
                "x": 100.0,
                "y": 100.0,
                "z": 100.0
            }
        }
        errors = await validator._validate_pattern_bounds(
            pattern,
            validator._rules["patterns"]["limits"]
        )
        assert len(errors) == 1
        assert "Pattern exceeds stage limits" in errors[0]

    async def test_validate_pattern_speed_exceed_limit(self, validator):
        """Test pattern speed exceeding limit."""
        pattern = {
            "type": "serpentine",
            "params": {
                "length": 500.0,
                "spacing": 10.0
            },
            "position": {
                "x": 100.0,
                "y": 100.0,
                "z": 100.0
            },
            "speed": 150.0  # Exceeds max speed
        }
        errors = await validator._validate_pattern_bounds(
            pattern,
            validator._rules["patterns"]["limits"]
        )
        assert len(errors) == 1
        assert "Speed exceeds maximum allowed" in errors[0]

    async def test_validate_serpentine_success(self, validator):
        """Test successful serpentine pattern validation."""
        pattern = {
            "type": "serpentine",
            "params": {
                "length": 500.0,
                "spacing": 10.0,
                "speed": 50.0,
                "offset": 5.0
            }
        }
        errors = await validator._validate_serpentine_pattern(pattern)
        assert len(errors) == 0

    async def test_validate_serpentine_missing_required(self, validator):
        """Test serpentine pattern with missing required fields."""
        pattern = {
            "type": "serpentine",
            "params": {
                "speed": 50.0
            }
        }
        errors = await validator._validate_serpentine_pattern(pattern)
        assert len(errors) == 2
        assert any("Missing required field: length" in error for error in errors)
        assert any("Missing required field: spacing" in error for error in errors)

    async def test_validate_serpentine_unknown_params(self, validator):
        """Test serpentine pattern with unknown parameters."""
        pattern = {
            "type": "serpentine",
            "params": {
                "length": 500.0,
                "spacing": 10.0,
                "unknown": 42.0
            }
        }
        errors = await validator._validate_serpentine_pattern(pattern)
        assert len(errors) == 1
        assert "Unknown field: unknown" in errors[0]

    async def test_validate_serpentine_invalid_values(self, validator):
        """Test serpentine pattern with invalid parameter values."""
        pattern = {
            "type": "serpentine",
            "params": {
                "length": -500.0,  # Invalid negative value
                "spacing": -10.0  # Invalid negative value
            }
        }
        errors = await validator._validate_serpentine_pattern(pattern)
        assert len(errors) == 2
        assert any("below minimum: 0" in error for error in errors)
        assert any("below minimum: 0" in error for error in errors)

    async def test_validate_spiral_success(self, validator):
        """Test successful spiral pattern validation."""
        pattern = {
            "type": "spiral",
            "params": {
                "diameter": 200.0,
                "pitch": 5.0,
                "speed": 50.0,
                "revolutions": 3
            }
        }
        errors = await validator._validate_spiral_pattern(pattern)
        assert len(errors) == 0

    async def test_validate_spiral_missing_required(self, validator):
        """Test spiral pattern with missing required fields."""
        pattern = {
            "type": "spiral",
            "params": {
                "speed": 50.0
            }
        }
        errors = await validator._validate_spiral_pattern(pattern)
        assert len(errors) == 2
        assert any("Missing required field: diameter" in error for error in errors)
        assert any("Missing required field: pitch" in error for error in errors)

    async def test_validate_spiral_unknown_params(self, validator):
        """Test spiral pattern with unknown parameters."""
        pattern = {
            "type": "spiral",
            "params": {
                "diameter": 200.0,
                "pitch": 5.0,
                "unknown": 42.0
            }
        }
        errors = await validator._validate_spiral_pattern(pattern)
        assert len(errors) == 1
        assert "Unknown field: unknown" in errors[0]

    async def test_validate_spiral_invalid_values(self, validator):
        """Test spiral pattern with invalid parameter values."""
        pattern = {
            "type": "spiral",
            "params": {
                "diameter": -200.0,  # Invalid negative value
                "pitch": -5.0  # Invalid negative value
            }
        }
        errors = await validator._validate_spiral_pattern(pattern)
        assert len(errors) == 2
        assert any("below minimum: 0" in error for error in errors)
        assert any("below minimum: 0" in error for error in errors)

    async def test_validate_full_serpentine_success(self, validator):
        """Test full validation of valid serpentine pattern."""
        pattern = {
            "type": "serpentine",
            "params": {
                "length": 500.0,
                "spacing": 10.0,
                "speed": 50.0
            },
            "position": {
                "x": 100.0,
                "y": 100.0,
                "z": 100.0
            }
        }
        result = await validator.validate(pattern)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    async def test_validate_full_spiral_success(self, validator):
        """Test full validation of valid spiral pattern."""
        pattern = {
            "type": "spiral",
            "params": {
                "diameter": 200.0,
                "pitch": 5.0,
                "speed": 50.0
            },
            "position": {
                "x": 100.0,
                "y": 100.0,
                "z": 100.0
            }
        }
        result = await validator.validate(pattern)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    async def test_validate_config_service_error(self, validator, mock_config_service):
        """Test validation with config service error."""
        mock_config_service.get_config.side_effect = Exception("Config error")
        pattern = {
            "type": "serpentine",
            "params": {
                "length": 500.0,
                "spacing": 10.0
            },
            "position": {
                "x": 100.0,
                "y": 100.0,
                "z": 100.0
            }
        }
        with pytest.raises(ValidationError) as exc_info:
            await validator.validate(pattern)
        assert "Pattern validation failed" in str(exc_info.value)
