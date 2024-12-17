"""Tests for sequence validator."""

import pytest
from unittest.mock import AsyncMock
from typing import Dict, Any
from datetime import datetime

from micro_cold_spray.api.validation.validators.sequence_validator import SequenceValidator
from micro_cold_spray.api.validation.exceptions import ValidationError
from micro_cold_spray.api.messaging import MessagingService


@pytest.fixture
def validation_rules() -> Dict[str, Any]:
    """Create test validation rules."""
    return {
        "sequences": {
            "required_fields": {
                "fields": ["name", "type", "steps"]
            },
            "max_steps": 10,
            "step_fields": {
                "required_fields": {
                    "fields": ["name"]
                },
                "optional_fields": {
                    "fields": ["description", "timeout", "action", "parameters"]
                }
            },
            "valid_actions": ["start", "stop", "pause", "resume"],
            "actions": {
                "start": {
                    "required_parameters": ["speed", "pressure"]
                },
                "stop": {
                    "required_parameters": ["mode"]
                },
                "pause": {
                    "required_parameters": []
                },
                "resume": {
                    "required_parameters": []
                }
            },
            "types": {
                "spray": {
                    "required_steps": ["start", "stop"],
                    "check_order": True,
                    "step_order": ["start", "stop"],
                    "optional_steps": ["pause", "resume"]
                },
                "calibration": {
                    "required_steps": ["start", "stop"],
                    "check_order": False
                }
            },
            "safety": {
                "enabled": True
            }
        }
    }


@pytest.fixture
def mock_message_broker():
    """Create mock message broker."""
    return AsyncMock(spec=MessagingService)


@pytest.fixture
def validator(validation_rules, mock_message_broker):
    """Create sequence validator instance."""
    return SequenceValidator(validation_rules, mock_message_broker)


class TestSequenceValidator:
    """Test sequence validator functionality."""

    async def test_initialization(self, validator, validation_rules, mock_message_broker):
        """Test validator initialization."""
        assert validator._rules == validation_rules
        assert validator._message_broker == mock_message_broker
        assert validator._hardware_validator is not None

    async def test_validate_missing_required_fields(self, validator):
        """Test validation with missing required fields."""
        result = await validator.validate({})
        assert result["valid"] is False
        assert len(result["errors"]) == 3
        assert any("Missing required field: name" in error for error in result["errors"])
        assert any("Missing required field: type" in error for error in result["errors"])
        assert any("Missing required field: steps" in error for error in result["errors"])

    async def test_validate_metadata_success(self, validator):
        """Test successful metadata validation."""
        metadata = {
            "name": "Test Sequence",
            "version": "1.0.0",
            "created": datetime.now().isoformat()
        }
        errors = await validator._validate_metadata(metadata)
        assert len(errors) == 0

    async def test_validate_metadata_missing_fields(self, validator):
        """Test metadata validation with missing fields."""
        metadata = {
            "name": "Test Sequence"
        }
        errors = await validator._validate_metadata(metadata)
        assert len(errors) == 2
        assert any("Missing required field: version" in error for error in errors)
        assert any("Missing required field: created" in error for error in errors)

    async def test_validate_metadata_invalid_timestamp(self, validator):
        """Test metadata validation with invalid timestamp."""
        metadata = {
            "name": "Test Sequence",
            "version": "1.0.0",
            "created": "invalid-timestamp"
        }
        errors = await validator._validate_metadata(metadata)
        assert len(errors) == 1
        assert "Invalid created timestamp format" in errors[0]

    async def test_validate_sequence_step_success(self, validator):
        """Test successful sequence step validation."""
        step = {
            "name": "Test Step",
            "description": "Test step description",
            "action": "start",
            "parameters": {
                "speed": 100.0,
                "pressure": 50.0
            }
        }
        errors = await validator._validate_sequence_step(step)
        assert len(errors) == 0

    async def test_validate_sequence_step_missing_fields(self, validator):
        """Test sequence step validation with missing fields."""
        step = {
            "action": "start"
        }
        errors = await validator._validate_sequence_step(step)
        assert len(errors) == 1
        assert "Missing required field: name" in errors[0]

    async def test_validate_sequence_step_unknown_fields(self, validator):
        """Test sequence step validation with unknown fields."""
        step = {
            "name": "Test Step",
            "unknown": "value"
        }
        errors = await validator._validate_sequence_step(step)
        assert len(errors) == 1
        assert "Unknown field: unknown" in errors[0]

    async def test_validate_action_step_success(self, validator):
        """Test successful action step validation."""
        step = {
            "name": "Start Step",
            "action": "start",
            "parameters": {
                "speed": 100.0,
                "pressure": 50.0
            }
        }
        errors = await validator._validate_action_step(step)
        assert len(errors) == 0

    async def test_validate_action_step_invalid_action(self, validator):
        """Test action step validation with invalid action."""
        step = {
            "name": "Invalid Step",
            "action": "invalid",
            "parameters": {}
        }
        errors = await validator._validate_action_step(step)
        assert len(errors) == 1
        assert "Invalid action type: invalid" in errors[0]

    async def test_validate_action_step_missing_parameters(self, validator):
        """Test action step validation with missing parameters."""
        step = {
            "name": "Start Step",
            "action": "start",
            "parameters": {
                "speed": 100.0
            }
        }
        errors = await validator._validate_action_step(step)
        assert len(errors) == 1
        assert "Missing required field: pressure" in errors[0]

    async def test_validate_sequence_type_success(self, validator):
        """Test successful sequence type validation."""
        sequence = {
            "type": "spray",
            "steps": [
                {
                    "name": "Start Step",
                    "action": "start",
                    "parameters": {
                        "speed": 100.0,
                        "pressure": 50.0
                    }
                },
                {
                    "name": "Stop Step",
                    "action": "stop",
                    "parameters": {
                        "mode": "normal"
                    }
                }
            ]
        }
        errors = await validator._validate_sequence_type(sequence)
        assert len(errors) == 0

    async def test_validate_sequence_type_with_optional_steps(self, validator):
        """Test sequence type validation with optional steps."""
        sequence = {
            "type": "spray",
            "steps": [
                {
                    "name": "Start Step",
                    "action": "start",
                    "parameters": {
                        "speed": 100.0,
                        "pressure": 50.0
                    }
                },
                {
                    "name": "Pause Step",
                    "action": "pause"
                },
                {
                    "name": "Resume Step",
                    "action": "resume"
                },
                {
                    "name": "Stop Step",
                    "action": "stop",
                    "parameters": {
                        "mode": "normal"
                    }
                }
            ]
        }
        errors = await validator._validate_sequence_type(sequence)
        assert len(errors) == 0

    async def test_validate_sequence_type_unknown(self, validator):
        """Test sequence type validation with unknown type."""
        sequence = {
            "type": "unknown",
            "steps": []
        }
        errors = await validator._validate_sequence_type(sequence)
        assert len(errors) == 1
        assert "Unknown sequence type: unknown" in errors[0]

    async def test_validate_sequence_type_missing_required_steps(self, validator):
        """Test sequence type validation with missing required steps."""
        sequence = {
            "type": "spray",
            "steps": [
                {
                    "name": "Start Step",
                    "action": "start",
                    "parameters": {
                        "speed": 100.0,
                        "pressure": 50.0
                    }
                }
            ]
        }
        errors = await validator._validate_sequence_type(sequence)
        assert len(errors) == 1
        assert "Missing required step: stop" in errors[0]

    async def test_validate_sequence_type_wrong_order(self, validator):
        """Test sequence type validation with wrong step order."""
        sequence = {
            "type": "spray",
            "steps": [
                {
                    "name": "Stop Step",
                    "action": "stop",
                    "parameters": {
                        "mode": "normal"
                    }
                },
                {
                    "name": "Start Step",
                    "action": "start",
                    "parameters": {
                        "speed": 100.0,
                        "pressure": 50.0
                    }
                }
            ]
        }
        errors = await validator._validate_sequence_type(sequence)
        assert len(errors) == 1
        assert "Invalid step order" in errors[0]

    async def test_validate_safety_conditions_success(self, validator):
        """Test successful safety conditions validation."""
        # Mock hardware validator to return no errors
        validator._hardware_validator.validate = AsyncMock(
            return_value={"valid": True, "errors": []}
        )
        errors = await validator._validate_safety_conditions()
        assert len(errors) == 0

    async def test_validate_safety_conditions_error(self, validator):
        """Test safety conditions validation with errors."""
        # Mock hardware validator to return errors
        validator._hardware_validator.validate = AsyncMock(
            return_value={"valid": False, "errors": ["Safety check failed"]}
        )
        errors = await validator._validate_safety_conditions()
        assert len(errors) == 1
        assert "Safety check failed" in errors[0]

    async def test_validate_full_sequence_success(self, validator):
        """Test successful full sequence validation."""
        sequence = {
            "name": "Test Sequence",
            "type": "spray",
            "metadata": {
                "name": "Test Sequence",
                "version": "1.0.0",
                "created": datetime.now().isoformat()
            },
            "steps": [
                {
                    "name": "Start Step",
                    "action": "start",
                    "parameters": {
                        "speed": 100.0,
                        "pressure": 50.0
                    }
                },
                {
                    "name": "Stop Step",
                    "action": "stop",
                    "parameters": {
                        "mode": "normal"
                    }
                }
            ]
        }
        # Mock hardware validator to return no errors
        validator._hardware_validator.validate = AsyncMock(
            return_value={"valid": True, "errors": []}
        )
        result = await validator.validate(sequence)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    async def test_validate_full_sequence_too_many_steps(self, validator):
        """Test sequence validation with too many steps."""
        steps = []
        for i in range(15):  # More than max_steps (10)
            steps.append({
                "name": f"Step {i}",
                "action": "start",
                "parameters": {
                    "speed": 100.0,
                    "pressure": 50.0
                }
            })
        sequence = {
            "name": "Test Sequence",
            "type": "spray",
            "steps": steps
        }
        result = await validator.validate(sequence)
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "exceeds maximum steps" in result["errors"][0]

    async def test_validate_hardware_validator_error(self, validator):
        """Test validation with hardware validator error."""
        sequence = {
            "name": "Test Sequence",
            "type": "spray",
            "steps": [
                {
                    "name": "Start Step",
                    "action": "start",
                    "parameters": {
                        "speed": 100.0,
                        "pressure": 50.0
                    }
                }
            ],
            "safety": {
                "enabled": True
            }
        }
        # Mock hardware validator to raise error
        validator._hardware_validator.validate = AsyncMock(
            side_effect=ValidationError("Hardware validation failed", {})
        )
        with pytest.raises(ValidationError) as exc_info:
            await validator.validate(sequence)
        assert "Sequence validation failed" in str(exc_info.value)
