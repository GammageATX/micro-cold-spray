"""Tests for parameter validator."""

import pytest
from unittest.mock import AsyncMock
from typing import Dict, Any

from micro_cold_spray.api.validation.validators.parameter_validator import ParameterValidator
from micro_cold_spray.api.validation.exceptions import ValidationError
from micro_cold_spray.api.messaging import MessagingService


@pytest.fixture
def validation_rules() -> Dict[str, Any]:
    """Create test validation rules."""
    return {
        "parameters": {
            "required_fields": {
                "fields": ["gas_flows", "powder_feed", "material"]
            },
            "gas_flows": {
                "gas_type": {
                    "choices": ["nitrogen", "helium", "air"]
                },
                "main_gas": {
                    "min": 0,
                    "max": 1000
                },
                "feeder_gas": {
                    "min": 0,
                    "max": 100
                }
            },
            "powder_feed": {
                "frequency": {
                    "min": 0,
                    "max": 100
                },
                "deagglomerator": {
                    "speed": {
                        "choices": ["low", "medium", "high"]
                    }
                }
            },
            "material": {
                "required_fields": {
                    "fields": ["type", "particle_size"]
                },
                "optional_fields": {
                    "fields": ["lot_number", "supplier"]
                },
                "type": {
                    "choices": ["copper", "aluminum", "steel"]
                },
                "particle_size": {
                    "min": 5,
                    "max": 100
                }
            }
        }
    }


@pytest.fixture
def mock_message_broker():
    """Create mock message broker."""
    broker = AsyncMock(spec=MessagingService)
    return broker


@pytest.fixture
def validator(validation_rules, mock_message_broker):
    """Create parameter validator instance."""
    return ParameterValidator(validation_rules, mock_message_broker)


class TestParameterValidator:
    """Test parameter validator functionality."""

    async def test_validate_valid_parameters(self, validator):
        """Test validation of valid parameters."""
        data = {
            "gas_flows": {
                "gas_type": "nitrogen",
                "main_gas": 500,
                "feeder_gas": 50
            },
            "powder_feed": {
                "frequency": 60,
                "deagglomerator": {
                    "speed": "medium"
                }
            },
            "material": {
                "type": "copper",
                "particle_size": 45,
                "lot_number": "ABC123"
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "warnings" in result

    async def test_validate_missing_required_fields(self, validator):
        """Test validation with missing required fields."""
        data = {
            "gas_flows": {
                "gas_type": "nitrogen"
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("Missing required field" in error for error in result["errors"])

    async def test_validate_invalid_gas_type(self, validator):
        """Test validation with invalid gas type."""
        data = {
            "gas_flows": {
                "gas_type": "invalid_gas",
                "main_gas": 500,
                "feeder_gas": 50
            },
            "powder_feed": {
                "frequency": 60,
                "deagglomerator": {"speed": "medium"}
            },
            "material": {
                "type": "copper",
                "particle_size": 45
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is False
        assert any("Gas type must be one of" in error for error in result["errors"])

    async def test_validate_gas_flow_limits(self, validator):
        """Test validation of gas flow limits."""
        data = {
            "gas_flows": {
                "gas_type": "nitrogen",
                "main_gas": 1500,  # Exceeds max
                "feeder_gas": -10  # Below min
            },
            "powder_feed": {
                "frequency": 60,
                "deagglomerator": {"speed": "medium"}
            },
            "material": {
                "type": "copper",
                "particle_size": 45
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is False
        assert any("above maximum" in error for error in result["errors"])
        assert any("below minimum" in error for error in result["errors"])

    async def test_validate_powder_feed_parameters(self, validator):
        """Test validation of powder feed parameters."""
        data = {
            "gas_flows": {
                "gas_type": "nitrogen",
                "main_gas": 500,
                "feeder_gas": 50
            },
            "powder_feed": {
                "frequency": 150,  # Exceeds max
                "deagglomerator": {
                    "speed": "invalid_speed"  # Invalid choice
                }
            },
            "material": {
                "type": "copper",
                "particle_size": 45
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is False
        assert any("above maximum" in error for error in result["errors"])
        assert any("must be one of" in error for error in result["errors"])

    async def test_validate_material_parameters(self, validator):
        """Test validation of material parameters."""
        data = {
            "gas_flows": {
                "gas_type": "nitrogen",
                "main_gas": 500,
                "feeder_gas": 50
            },
            "powder_feed": {
                "frequency": 60,
                "deagglomerator": {"speed": "medium"}
            },
            "material": {
                "type": "invalid_material",  # Invalid type
                "particle_size": 150,  # Exceeds max
                "unknown_field": "value"  # Unknown field
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is False
        assert any("must be one of" in error for error in result["errors"])
        assert any("above maximum" in error for error in result["errors"])
        assert any("Unknown field" in error for error in result["errors"])

    async def test_validate_non_numeric_values(self, validator):
        """Test validation with non-numeric values for numeric fields."""
        data = {
            "gas_flows": {
                "gas_type": "nitrogen",
                "main_gas": "not_a_number",
                "feeder_gas": 50
            },
            "powder_feed": {
                "frequency": 60,
                "deagglomerator": {"speed": "medium"}
            },
            "material": {
                "type": "copper",
                "particle_size": 45
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is False
        assert any("must be numeric" in error for error in result["errors"])

    async def test_validate_null_values(self, validator):
        """Test validation with null values."""
        data = {
            "gas_flows": {
                "gas_type": None,
                "main_gas": 500,
                "feeder_gas": 50
            },
            "powder_feed": {
                "frequency": 60,
                "deagglomerator": {"speed": "medium"}
            },
            "material": {
                "type": "copper",
                "particle_size": None
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is False
        assert any("cannot be null" in error for error in result["errors"])

    async def test_validation_error_handling(self, validator):
        """Test error handling during validation."""
        # Simulate an error by providing invalid rules
        validator._rules = None

        with pytest.raises(ValidationError) as exc_info:
            await validator.validate({})
        
        assert "Parameter validation failed" in str(exc_info.value)

    async def test_validate_empty_data(self, validator):
        """Test validation with empty data."""
        result = await validator.validate({})
        assert result["valid"] is False
        assert any("Missing required field" in error for error in result["errors"])

    async def test_validate_missing_gas_flows(self, validator):
        """Test validation with missing gas flows section."""
        data = {
            "powder_feed": {
                "frequency": 60,
                "deagglomerator": {"speed": "medium"}
            },
            "material": {
                "type": "copper",
                "particle_size": 45
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is False
        assert any("Missing required field: gas_flows" in error for error in result["errors"])

    async def test_validate_partial_gas_flows(self, validator):
        """Test validation with partial gas flows data."""
        data = {
            "gas_flows": {
                "gas_type": "nitrogen"
                # Missing main_gas and feeder_gas
            },
            "powder_feed": {
                "frequency": 60,
                "deagglomerator": {"speed": "medium"}
            },
            "material": {
                "type": "copper",
                "particle_size": 45
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    async def test_validate_invalid_material_type_none(self, validator):
        """Test validation with None material type."""
        data = {
            "gas_flows": {
                "gas_type": "nitrogen",
                "main_gas": 500,
                "feeder_gas": 50
            },
            "powder_feed": {
                "frequency": 60,
                "deagglomerator": {"speed": "medium"}
            },
            "material": {
                "type": None,
                "particle_size": 45
            }
        }

        result = await validator.validate(data)
        assert result["valid"] is False
        assert any("cannot be null" in error for error in result["errors"])
