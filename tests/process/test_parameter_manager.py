"""Parameter Manager test suite.

Tests parameter management according to .cursorrules:
- Parameter validation
- Parameter loading
- Parameter saving
- Error handling

Run with:
    pytest tests/operations/test_parameter_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any
import asyncio
from tests.conftest import TestOrder, order

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.process.operations.parameters.parameter_manager import ParameterManager


@pytest.fixture
async def parameter_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    process_validator: ProcessValidator
):
    """Provide ParameterManager instance."""
    manager = ParameterManager(
        message_broker=message_broker,
        config_manager=config_manager,
        process_validator=process_validator
    )
    await manager.initialize()
    yield manager
    await manager.shutdown()


@order(TestOrder.OPERATIONS)
class TestParameterManager:
    """Parameter management tests."""

    @pytest.mark.asyncio
    async def test_parameter_validation(self, parameter_manager):
        """Test parameter validation."""
        # Track validation responses
        responses = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        await parameter_manager._message_broker.subscribe(
            "parameters/loaded",
            collect_responses
        )

        # Send test parameters
        test_params = {
            "gas": {
                "type": "helium",
                "main_flow": 50.0
            }
        }
        await parameter_manager._message_broker.publish(
            "parameters/validate",
            test_params
        )
        await asyncio.sleep(0.1)

        # Verify validation
        assert len(responses) > 0
        assert responses[0]["validation"]["valid"]
        assert responses[0]["parameters"] == test_params

    @pytest.mark.asyncio
    async def test_parameter_loading(self, parameter_manager):
        """Test parameter loading."""
        # Track validation responses
        responses = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        await parameter_manager._message_broker.subscribe(
            "validation/response",
            collect_responses
        )

        # Send test parameters
        test_params = {
            "file": "test_params.yaml"
        }
        await parameter_manager._message_broker.publish(
            "parameters/load",
            test_params
        )
        await asyncio.sleep(0.1)

        # Verify loading
        assert len(responses) > 0
        assert responses[0]["result"]["valid"]
        assert responses[0]["request_type"] == "parameters"

    @pytest.mark.asyncio
    async def test_parameter_saving(self, parameter_manager):
        """Test parameter saving."""
        # Track parameter messages
        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await parameter_manager._message_broker.subscribe(
            "parameters/saved",
            collect_messages
        )

        # Send test parameters
        test_params = {
            "gas": {
                "type": "helium",
                "main_flow": 50.0
            }
        }
        await parameter_manager._message_broker.publish(
            "parameters/save",
            {
                "name": "test_params",
                "parameters": test_params
            }
        )
        await asyncio.sleep(0.1)

        # Verify saving
        assert len(messages) > 0
        assert messages[0]["file"].endswith("test_params.yaml")
        assert messages[0]["parameters"] == test_params

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

        # Send invalid parameters
        test_params = {
            "gas": {
                "type": "invalid_gas",
                "main_flow": -1.0
            }
        }
        await parameter_manager._message_broker.publish(
            "parameters/validate",
            test_params
        )
        await asyncio.sleep(0.1)

        # Verify error handling
        assert len(errors) > 0
        assert "error" in errors[0]
        assert "parameters" in errors[0]
