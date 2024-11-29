"""Process Validator test suite.

Tests process validation according to process.yaml:
- Parameter validation rules
- Pattern validation rules
- Sequence validation rules
- Hardware set validation
- Process state validation

Validation Rules (from process.yaml):
- Process parameters (gas, powder, environment)
- Pattern limits (position, speed)
- Sequence rules (steps, safe position, spray conditions)
- Hardware set rules (feeder/nozzle matching)
- Process state rules (gas flow, chamber vacuum, etc.)

Run with:
    pytest tests/test_process_validator.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order

@order(TestOrder.PROCESS)
class TestProcessValidator:
    """Process validation tests."""
    
    @pytest.mark.asyncio
    async def test_validate_gas_parameters(self, process_validator):
        """Test gas parameter validation."""
        # Test parameters from process.yaml gas section
        parameters = {
            "gas": {
                "type": "helium",
                "main_flow": 50.0,
                "feeder_flow": 5.0
            }
        }
        
        result = await process_validator.validate_parameters(parameters)
        assert result["valid"]
        assert len(result["errors"]) == 0
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_validate_powder_parameters(self, process_validator):
        """Test powder parameter validation."""
        # Test parameters from process.yaml powder section
        parameters = {
            "powder": {
                "feeder": {
                    "frequency": 600,  # Within range from process.yaml
                    "deagglomerator": {
                        "duty_cycle": 35,  # Default from process.yaml
                        "frequency": 500
                    }
                }
            }
        }
        
        result = await process_validator.validate_parameters(parameters)
        assert result["valid"]
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_pattern_limits(self, process_validator):
        """Test pattern validation against limits."""
        pattern_data = {
            "type": "serpentine",
            "pattern_data": {
                "origin": [0.0, 0.0],  # Outside sprayable area
                "length": 600.0,       # Exceeds limits
                "spacing": 2.0,
                "speed": 20.0
            }
        }
        
        # Track validation responses
        responses = []
        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)
        await process_validator._message_broker.subscribe(
            "validation/response",
            collect_responses
        )
        
        # Send validation request
        await process_validator._message_broker.publish(
            "validation/request",
            {
                "type": "pattern",
                "data": pattern_data
            }
        )
        await asyncio.sleep(0.1)
        
        # Verify validation response
        assert len(responses) > 0
        result = responses[0]["result"]
        assert not result["valid"]
        assert any("exceeds sprayable area" in str(err) for err in result["errors"])
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_validate_sequence_rules(self, process_validator):
        """Test sequence validation rules."""
        sequence_data = {
            "steps": [
                {
                    "action": "move_to_trough",
                    "parameters": {}
                },
                {
                    "action": "start_gas_flow",
                    "parameters": {
                        "main_flow": 50.0
                    }
                }
            ]
        }
        
        result = await process_validator.validate_sequence(sequence_data)
        assert result["valid"]
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_hardware_set_rules(self, process_validator):
        """Test hardware set validation rules."""
        # Test validation of feeder/nozzle matching
        validation_data = {
            "active_set": "set1",
            "components": {
                "nozzle": "nozzle1",
                "feeder": "feeder1",
                "deagglomerator": "deagg1"
            }
        }
        
        # Track validation responses
        responses = []
        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)
        await process_validator._message_broker.subscribe(
            "validation/response",
            collect_responses
        )
        
        await process_validator._handle_validation_request({
            "type": "hardware_sets",
            "data": validation_data
        })
        await asyncio.sleep(0.1)
        
        # Verify validation response
        assert len(responses) > 0
        assert responses[0]["result"]["valid"], f"Validation failed: {responses[0]['result']['errors']}"
        assert "timestamp" in responses[0]["result"]

    @pytest.mark.asyncio
    async def test_validate_process_states(self, process_validator):
        """Test process state validation rules."""
        # Test gas flow stability validation
        state_data = {
            "gas_control.main_flow.measured": 50.0,
            "gas_control.main_flow.setpoint": 50.0,
            "gas_control.feeder_flow.measured": 5.0,
            "gas_control.feeder_flow.setpoint": 5.0
        }
        
        result = await process_validator._validate_process_params(
            state_data,
            process_validator._config_manager.get_config("process"),
            {"errors": [], "warnings": []}
        )
        
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validation_message_patterns(self, process_validator):
        """Test validation message patterns."""
        # Track validation messages
        messages = []
        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
            
        await process_validator._message_broker.subscribe(
            "validation/response",
            collect_messages
        )
        
        # Send validation request
        await process_validator._message_broker.publish(
            "validation/request",
            {
                "type": "parameters",
                "parameters": {
                    "gas": {
                        "type": "helium",
                        "main_flow": 50.0
                    }
                }
            }
        )
        await asyncio.sleep(0.1)
        
        # Verify message compliance
        assert len(messages) > 0
        assert "result" in messages[0]
        assert "timestamp" in messages[0]
        assert messages[0]["result"]["valid"]