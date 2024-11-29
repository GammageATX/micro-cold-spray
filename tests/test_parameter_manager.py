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
from typing import Dict, Any
import asyncio
from datetime import datetime
from pathlib import Path
import yaml
from tests.conftest import TestOrder, order

@pytest.fixture
async def parameter_manager(
    message_broker,
    config_manager,
    process_validator
):
    """Provide ParameterManager instance."""
    from micro_cold_spray.core.components.operations.parameters.parameter_manager import ParameterManager
    
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

@order(TestOrder.PROCESS)
class TestParameterManager:
    """Parameter management tests."""
    
    @pytest.mark.asyncio
    async def test_parameter_manager_initialization(self, parameter_manager):
        """Test parameter manager initialization."""
        assert parameter_manager._is_initialized
        process_config = await parameter_manager._config_manager.get_config('process')
        assert 'parameters' in process_config

    @pytest.mark.asyncio
    async def test_load_gas_parameters(self, parameter_manager):
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
    async def test_validate_powder_parameters(self, parameter_manager):
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
        await asyncio.sleep(0.2)
        
        # Verify validation
        assert len(responses) > 0
        assert responses[0]["result"]["valid"]
        assert "timestamp" in responses[0]

    @pytest.mark.asyncio
    async def test_parameter_message_patterns(self, parameter_manager):
        """Test parameter-related message patterns."""
        # Track parameter messages
        messages = []
        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
            
        await parameter_manager._message_broker.subscribe(
            "parameters/saved",
            collect_messages
        )
        
        # Save parameters
        parameters = {
            "gas": {
                "type": "helium",
                "main_flow": 50.0
            }
        }
        await parameter_manager.save_parameters("test_params", parameters)
        await asyncio.sleep(0.2)
        
        # Verify message compliance
        assert len(messages) > 0
        assert "timestamp" in messages[0]
        assert messages[0]["filename"] == "test_params"

    @pytest.mark.asyncio
    async def test_parameter_error_handling(self, parameter_manager):
        """Test parameter error handling."""
        # Track error messages
        errors = []
        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)
            
        await parameter_manager._message_broker.subscribe(
            "parameters/error",
            collect_errors
        )
        
        # Try to load invalid parameters
        with pytest.raises(Exception):
            await parameter_manager.load_parameters({
                "gas": {
                    "type": "invalid_gas",
                    "main_flow": -1.0  # Invalid value
                }
            })
        await asyncio.sleep(0.2)
        
        # Verify error handling
        assert len(errors) > 0
        assert "error" in errors[0]
        assert "timestamp" in errors[0]