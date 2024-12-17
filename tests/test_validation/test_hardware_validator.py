"""Tests for hardware validator."""

import pytest
from unittest.mock import AsyncMock
from typing import Dict, Any

from micro_cold_spray.api.validation.validators.hardware_validator import (
    HardwareValidator,
    HardwareState
)
from micro_cold_spray.api.validation.exceptions import ValidationError
from micro_cold_spray.api.messaging import MessagingService


@pytest.fixture
def validation_rules() -> Dict[str, Any]:
    """Create test validation rules."""
    return {
        "states": {
            "chamber_vacuum": {
                "checks": [{
                    "value": 100.0,
                    "message": "Chamber pressure too high"
                }]
            }
        },
        "validation": {
            "gas_pressure": {
                "min_margin": 50.0,
                "message": "Main pressure too low"
            },
            "flow_stability": {
                "main_tolerance": 2.0,
                "feeder_tolerance": 1.0,
                "main_flow": {
                    "message": "Main flow unstable"
                },
                "feeder_flow": {
                    "message": "Feeder flow unstable"
                }
            }
        },
        "sequences": {
            "safe_position": {
                "message": "Z position below safe height"
            }
        }
    }


@pytest.fixture
def mock_message_broker():
    """Create mock message broker."""
    broker = AsyncMock(spec=MessagingService)
    
    # Setup default tag values
    tag_values = {
        "pressure.chamber_pressure": 50.0,
        "pressure.main_supply_pressure": 200.0,
        "pressure.regulator_pressure": 100.0,
        "motion.position.z_position": 100.0,
        "safety.safe_z": 50.0,
        "gas_control.main_flow.measured": 10.0,
        "gas_control.feeder_flow.measured": 5.0,
        "gas_control.main_flow.setpoint": 10.0,
        "gas_control.feeder_flow.setpoint": 5.0
    }
    
    async def mock_request(topic: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if topic == "tag/request" and "tag" in data:
            return {"value": tag_values.get(data["tag"], 0.0)}
        return {"value": 0.0}
    
    broker.request = AsyncMock(side_effect=mock_request)
    return broker


@pytest.fixture
def validator(validation_rules, mock_message_broker):
    """Create hardware validator instance."""
    return HardwareValidator(validation_rules, mock_message_broker)


class TestHardwareValidator:
    """Test hardware validator functionality."""

    async def test_initialization(self, validator, validation_rules):
        """Test validator initialization."""
        assert validator._rules == validation_rules
        assert validator._message_broker is not None

    async def test_get_hardware_state_success(self, validator):
        """Test successful hardware state retrieval."""
        state = await validator._get_hardware_state()
        assert isinstance(state, HardwareState)
        assert state.chamber_pressure == 50.0
        assert state.main_pressure == 200.0
        assert state.regulator_pressure == 100.0
        assert state.z_position == 100.0
        assert state.safe_z_height == 50.0
        assert state.main_flow == 10.0
        assert state.feeder_flow == 5.0
        assert state.main_flow_setpoint == 10.0
        assert state.feeder_flow_setpoint == 5.0

    async def test_get_hardware_state_error(self, validator, mock_message_broker):
        """Test hardware state retrieval error."""
        mock_message_broker.request.side_effect = Exception("Test error")
        with pytest.raises(ValidationError) as exc_info:
            await validator._get_hardware_state()
        assert "Failed to get hardware state" in str(exc_info.value)

    async def test_validate_chamber_pressure_success(self, validator):
        """Test successful chamber pressure validation."""
        state = HardwareState(chamber_pressure=50.0)
        errors = await validator._validate_chamber_pressure(state)
        assert len(errors) == 0

    async def test_validate_chamber_pressure_error(self, validator):
        """Test chamber pressure validation error."""
        state = HardwareState(chamber_pressure=150.0)
        errors = await validator._validate_chamber_pressure(state)
        assert len(errors) == 1
        assert "Chamber pressure too high" in errors[0]

    async def test_validate_gas_pressures_success(self, validator):
        """Test successful gas pressure validation."""
        state = HardwareState(main_pressure=200.0, regulator_pressure=100.0)
        errors = await validator._validate_gas_pressures(state)
        assert len(errors) == 0

    async def test_validate_gas_pressures_error(self, validator):
        """Test gas pressure validation error."""
        state = HardwareState(main_pressure=120.0, regulator_pressure=100.0)
        errors = await validator._validate_gas_pressures(state)
        assert len(errors) == 1
        assert "Main pressure too low" in errors[0]

    async def test_validate_position_success(self, validator):
        """Test successful position validation."""
        state = HardwareState(z_position=100.0, safe_z_height=50.0)
        errors = await validator._validate_position(state)
        assert len(errors) == 0

    async def test_validate_position_error(self, validator):
        """Test position validation error."""
        state = HardwareState(z_position=40.0, safe_z_height=50.0)
        errors = await validator._validate_position(state)
        assert len(errors) == 1
        assert "Z position below safe height" in errors[0]

    async def test_validate_flow_stability_success(self, validator):
        """Test successful flow stability validation."""
        state = HardwareState(
            main_flow=10.0,
            main_flow_setpoint=10.0,
            feeder_flow=5.0,
            feeder_flow_setpoint=5.0
        )
        errors = await validator._validate_flow_stability(state)
        assert len(errors) == 0

    async def test_validate_flow_stability_main_error(self, validator):
        """Test main flow stability validation error."""
        state = HardwareState(
            main_flow=15.0,
            main_flow_setpoint=10.0,
            feeder_flow=5.0,
            feeder_flow_setpoint=5.0
        )
        errors = await validator._validate_flow_stability(state)
        assert len(errors) == 1
        assert "Main flow unstable" in errors[0]

    async def test_validate_flow_stability_feeder_error(self, validator):
        """Test feeder flow stability validation error."""
        state = HardwareState(
            main_flow=10.0,
            main_flow_setpoint=10.0,
            feeder_flow=7.0,
            feeder_flow_setpoint=5.0
        )
        errors = await validator._validate_flow_stability(state)
        assert len(errors) == 1
        assert "Feeder flow unstable" in errors[0]

    async def test_validate_flow_stability_both_errors(self, validator):
        """Test both flows stability validation errors."""
        state = HardwareState(
            main_flow=15.0,
            main_flow_setpoint=10.0,
            feeder_flow=7.0,
            feeder_flow_setpoint=5.0
        )
        errors = await validator._validate_flow_stability(state)
        assert len(errors) == 2
        assert any("Main flow unstable" in error for error in errors)
        assert any("Feeder flow unstable" in error for error in errors)

    async def test_validate_success(self, validator):
        """Test successful full validation."""
        result = await validator.validate({})
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0

    async def test_validate_with_errors(self, validator, mock_message_broker):
        """Test validation with multiple errors."""
        error_tag_values = {
            "pressure.chamber_pressure": 150.0,  # Too high
            "pressure.main_supply_pressure": 120.0,  # Too low margin
            "pressure.regulator_pressure": 100.0,
            "motion.position.z_position": 40.0,  # Below safe height
            "safety.safe_z": 50.0,
            "gas_control.main_flow.measured": 15.0,  # Unstable
            "gas_control.feeder_flow.measured": 7.0,  # Unstable
            "gas_control.main_flow.setpoint": 10.0,
            "gas_control.feeder_flow.setpoint": 5.0
        }
        
        async def mock_error_request(topic: str, data: Dict[str, Any]) -> Dict[str, Any]:
            if topic == "tag/request" and "tag" in data:
                return {"value": error_tag_values.get(data["tag"], 0.0)}
            return {"value": 0.0}
        
        mock_message_broker.request = AsyncMock(side_effect=mock_error_request)
        
        result = await validator.validate({})
        assert result["valid"] is False
        assert len(result["errors"]) == 5  # All validation checks should fail
        assert len(result["warnings"]) == 0

    async def test_validate_broker_error(self, validator, mock_message_broker):
        """Test validation with broker error."""
        mock_message_broker.request.side_effect = Exception("Test error")
        with pytest.raises(ValidationError) as exc_info:
            await validator.validate({})
        assert "Hardware validation failed" in str(exc_info.value)
