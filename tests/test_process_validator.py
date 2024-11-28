"""Process Validator test suite.

Tests validation according to process.yaml rules:
- Process parameter validation
- Pattern limit validation
- Sequence rule validation
- Hardware set validation
- Safety rule validation

Key Requirements:
- Must use MessageBroker for all communication
- Must validate against process.yaml rules
- Must handle async operations
- Must include timestamps

Run with:
    pytest tests/test_process_validator.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from tests.conftest import TestOrder

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.exceptions import ValidationError

@TestOrder.PROCESS
class TestProcessValidator:
    """Process validation tests run after monitors."""
    
    @pytest.mark.asyncio
    async def test_process_validator_initialization(self, process_validator):
        """Test process validator initialization."""
        assert process_validator._is_initialized
        assert 'validation' in process_validator._config_manager.get_config('process')
    
    @pytest.mark.asyncio
    async def test_process_validator_validate_parameters(self, process_validator):
        """Test parameter validation using real rules."""
        # Test parameters matching process.yaml rules
        parameters = {
            "chamber_pressure": 2.0,  # Below spray_threshold
            "gas_pressure": {
                "main_pressure": 80.0,
                "regulator_pressure": 60.0  # Maintains min_margin
            }
        }
        result = await process_validator.validate_parameters(parameters)
        assert result["valid"]

@pytest.mark.asyncio
async def test_process_validator_invalid_parameters(process_validator):
    """Test invalid parameter validation."""
    # Test parameters violating process.yaml rules
    parameters = {
        "chamber_pressure": 10.0,  # Above spray_threshold
        "gas_pressure": {
            "main_pressure": 50.0,
            "regulator_pressure": 60.0  # Violates min_margin
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
    
    # Request validation
    await process_validator._message_broker.publish(
        "validation/request",
        {
            "type": "process_parameters",
            "parameters": parameters,
            "timestamp": datetime.now().isoformat()
        }
    )
    await asyncio.sleep(0.1)
    
    # Verify response
    assert len(responses) > 0
    assert not responses[0]["valid"]
    assert len(responses[0]["errors"]) > 0
    assert "timestamp" in responses[0]