"""Process Validator test suite.

Tests process validation according to process.yaml:
- Parameter validation rules
- Pattern validation rules
- Sequence validation rules
- Hardware set validation
- Process state validation

Run with:
    pytest tests/test_process_validator.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order

@order(TestOrder.PROCESS)
class TestProcessValidator:
    """Process validation tests."""
    
    @pytest.mark.asyncio
    async def test_validate_gas_parameters(self, process_validator):
        """Test gas parameter validation."""
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
        parameters = {
            "powder": {
                "feeder": {
                    "frequency": 600,
                    "deagglomerator": {
                        "duty_cycle": 35,
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
        """Test pattern validation against stage dimensions."""
        pattern_data = {
            "pattern": {
                "type": "serpentine",
                "params": {
                    "origin": [0.0, 0.0],
                    "length": 300.0,  # Exceeds stage dimensions (200mm)
                    "spacing": 2.0,
                    "speed": 20.0
                }
            }
        }
        
        # Track validation responses
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
                "type": "pattern",
                "data": pattern_data,
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)
        
        # Verify validation response
        assert len(messages) > 0
        result = messages[0]["result"]
        assert not result["valid"]
        assert any("exceeds stage dimensions" in str(err) for err in result["errors"])

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
        validation_data = {
            "active_set": "set1",
            "components": {
                "nozzle": "nozzle1",
                "feeder": "feeder1",
                "deagglomerator": "deagg1"
            }
        }
        
        # Track validation responses
        messages = []
        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
        await process_validator._message_broker.subscribe(
            "validation/response",
            collect_messages
        )
        
        await process_validator._handle_validation_request({
            "type": "hardware_sets",
            "data": validation_data,
            "timestamp": datetime.now().isoformat()
        })
        await asyncio.sleep(0.1)
        
        # Verify validation response
        assert len(messages) > 0
        assert messages[0]["result"]["valid"]

    @pytest.mark.asyncio
    async def test_validate_process_states(self, process_validator):
        """Test process state validation rules."""
        state_data = {
            "gas_control.main_flow.measured": 50.0,
            "gas_control.main_flow.setpoint": 50.0,
            "gas_control.feeder_flow.measured": 5.0,
            "gas_control.feeder_flow.setpoint": 5.0
        }
        
        result = await process_validator._validate_process_params(
            state_data,
            await process_validator._config_manager.get_config("process"),
            {"errors": [], "warnings": []}
        )
        
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validation_message_patterns(self, process_validator):
        """Test validation message patterns."""
        messages = []
        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
            
        await process_validator._message_broker.subscribe(
            "validation/response",
            collect_messages
        )
        
        await process_validator._message_broker.publish(
            "validation/request",
            {
                "type": "parameters",
                "parameters": {
                    "gas": {
                        "type": "helium",
                        "main_flow": 50.0
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)
        
        assert len(messages) > 0
        assert "result" in messages[0]
        assert "timestamp" in messages[0]
        assert messages[0]["result"]["valid"]