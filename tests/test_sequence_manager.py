"""Sequence Manager test suite.

Tests sequence management according to .cursorrules:
- Sequence validation
- Sequence execution
- Parameter substitution
- Error handling

Run with:
    pytest tests/test_sequence_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
from tests.conftest import TestOrder, order

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.components.operations.patterns.pattern_manager import PatternManager
from micro_cold_spray.core.components.operations.actions.action_manager import ActionManager
from micro_cold_spray.core.components.operations.sequences.sequence_manager import SequenceManager


@pytest.fixture
async def sequence_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    process_validator: ProcessValidator,
    pattern_manager: PatternManager,
    action_manager: ActionManager
) -> AsyncGenerator[SequenceManager, None]:
    """Provide SequenceManager instance."""
    manager = SequenceManager(
        message_broker=message_broker,
        config_manager=config_manager,
        process_validator=process_validator,
        pattern_manager=pattern_manager,
        action_manager=action_manager
    )
    await manager.initialize()
    yield manager
    await manager.shutdown()


@order(TestOrder.PROCESS)
class TestSequenceManager:
    """Sequence management tests."""

    @pytest.mark.asyncio
    async def test_sequence_validation(self, sequence_manager):
        """Test sequence validation."""
        # Track sequence messages
        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await sequence_manager._message_broker.subscribe(
            "sequence/validation",
            collect_messages
        )

        # Send test sequence
        test_sequence = {
            "name": "test_sequence",
            "steps": [
                {
                    "action": "move_to",
                    "parameters": {
                        "x": 100.0,
                        "y": 100.0,
                        "z": 50.0
                    }
                }
            ]
        }
        await sequence_manager._message_broker.publish(
            "sequence/validate",
            test_sequence
        )
        await asyncio.sleep(0.1)

        # Verify validation
        assert len(messages) > 0
        assert messages[0]["is_valid"]

    @pytest.mark.asyncio
    async def test_sequence_execution(self, sequence_manager):
        """Test sequence execution."""
        # Track sequence operations
        operations = []

        async def collect_operations(data: Dict[str, Any]) -> None:
            operations.append(data)

        await sequence_manager._message_broker.subscribe(
            "sequence/step",
            collect_operations
        )

        # Send test sequence
        test_sequence = {
            "name": "test_sequence",
            "steps": [
                {
                    "action": "move_to",
                    "parameters": {
                        "x": 100.0,
                        "y": 100.0,
                        "z": 50.0
                    }
                }
            ]
        }
        await sequence_manager._message_broker.publish(
            "sequence/start",
            test_sequence
        )
        await asyncio.sleep(0.1)

        # Verify execution
        assert len(operations) > 0
        assert operations[0]["step"]["action"] == "move_to"

    @pytest.mark.asyncio
    async def test_sequence_state_transitions(self, sequence_manager):
        """Test sequence state transitions."""
        # Track state changes
        states = []

        async def collect_states(data: Dict[str, Any]) -> None:
            states.append(data)

        await sequence_manager._message_broker.subscribe(
            "sequence/state",
            collect_states
        )

        # Send test sequence
        test_sequence = {
            "name": "test_sequence",
            "steps": [
                {
                    "action": "move_to",
                    "parameters": {
                        "x": 100.0,
                        "y": 100.0,
                        "z": 50.0
                    }
                }
            ]
        }

        # Start sequence
        await sequence_manager._message_broker.publish(
            "sequence/start",
            test_sequence
        )
        await asyncio.sleep(0.1)

        # Verify state transitions
        assert len(states) > 0
        assert states[0]["state"] == "RUNNING"

    @pytest.mark.asyncio
    async def test_sequence_error_handling(self, sequence_manager):
        """Test sequence error handling."""
        # Track error messages
        errors = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        await sequence_manager._message_broker.subscribe(
            "sequence/error",
            collect_errors
        )

        # Send invalid sequence
        test_sequence = {
            "name": "test_sequence",
            "steps": [
                {
                    "action": "invalid_action",
                    "parameters": {}
                }
            ]
        }
        await sequence_manager._message_broker.publish(
            "sequence/start",
            test_sequence
        )
        await asyncio.sleep(0.1)

        # Verify error handling
        assert len(errors) > 0
        assert "invalid_action" in errors[0]["message"]
