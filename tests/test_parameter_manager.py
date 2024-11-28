"""Parameter Manager test suite.

Tests parameter management according to process.yaml:
- Parameter validation using process rules
- Parameter loading and saving
- Parameter application
- Message pattern compliance
- Error handling

Parameter Types (from process.yaml):
- Gas control parameters
- Powder system parameters
- Process environment parameters
- Motion pattern parameters

Run with:
    pytest tests/test_parameter_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from tests.conftest import TestOrder

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.operations.parameters.parameter_manager import ParameterManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.exceptions import ValidationError

@pytest.fixture
async def parameter_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    process_validator: ProcessValidator
) -> AsyncGenerator[ParameterManager, None]:
    """Provide a ParameterManager instance."""
    manager = ParameterManager(
        message_broker=message_broker,
        config_manager=config_manager,
        process_validator=process_validator
    )
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@TestOrder.PROCESS
class TestParameterManager:
    """Parameter management tests run after process validator."""
    
    @pytest.mark.asyncio
    async def test_parameter_manager_initialization(self, parameter_manager):
        """Test parameter manager initialization."""
        assert parameter_manager._is_initialized
        process_config = parameter_manager._config_manager.get_config('process')
        assert 'parameters' in process_config

@pytest.mark.asyncio
async def test_parameter_manager_load_gas_parameters(parameter_manager):
    """Test gas parameter loading with validation."""
    # Test loading gas parameters from process.yaml
    parameters = {
        "gas": {
            "type": "helium",
            "main_flow": 50.0,
            "feeder_flow": 5.0
        }
    }
    
    # Track validation responses
    responses = []
    async def collect_responses(data: Dict[str, Any]) -> None:
        responses.append(data)
    await parameter_manager._message_broker.subscribe(
        "parameters/loaded",
        collect_responses
    )
    
    # Load parameters
    await parameter_manager.load_parameters(parameters)
    await asyncio.sleep(0.1)
    
    # Verify response
    assert len(responses) > 0
    assert "timestamp" in responses[0]
    assert responses[0]["parameters"]["gas"]["type"] == "helium"

@pytest.mark.asyncio
async def test_parameter_manager_validate_powder_parameters(parameter_manager):
    """Test powder parameter validation."""
    # Test powder parameters from process.yaml
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
    
    # Track validation responses
    responses = []
    async def collect_responses(data: Dict[str, Any]) -> None:
        responses.append(data)
    await parameter_manager._message_broker.subscribe(
        "validation/response",
        collect_responses
    )
    
    # Validate parameters
    await parameter_manager.validate_parameters(parameters)
    await asyncio.sleep(0.1)
    
    # Verify validation
    assert len(responses) > 0
    assert responses[0]["valid"]
    assert "timestamp" in responses[0] 