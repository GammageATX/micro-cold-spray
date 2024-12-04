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
from pathlib import Path
from tests.conftest import TestOrder, order

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.components.operations.actions.action_manager import ActionManager
from micro_cold_spray.core.components.operations.sequences.sequence_manager import SequenceManager


@pytest.fixture
async def sequence_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    action_manager: ActionManager
) -> AsyncGenerator[SequenceManager, None]:
    """Provide SequenceManager instance."""
    manager = SequenceManager(
        message_broker=message_broker,
        config_manager=config_manager,
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
            "sequence/loaded",
            collect_messages
        )

        # Load test sequence
        test_sequence = {
            "sequence": {
                "metadata": {
                    "name": "Flow Study Test",
                    "version": "1.0",
                    "created": "2024-03-20",
                    "author": "Test Author",
                    "description": "Test sequence for validation"
                },
                "steps": [
                    {
                        "name": "Initialize",
                        "action_group": "ready_system"
                    },
                    {
                        "name": "Test Pattern",
                        "action_group": "execute_pattern",
                        "parameters": {
                            "pattern_file": "test_pattern.yaml",
                            "parameter_file": "test_params.yaml",
                            "passes": 1
                        }
                    }
                ]
            }
        }

        # Save sequence to temp file
        sequence_path = Path("data/sequences/library/test_sequence.yaml")
        sequence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sequence_path, "w") as f:
            import yaml
            yaml.dump(test_sequence, f)

        # Load sequence
        await sequence_manager._message_broker.publish(
            "sequence/load",
            {"filename": "test_sequence.yaml"}
        )
        await asyncio.sleep(0.2)

        # Verify validation
        assert len(messages) > 0
        assert messages[0]["sequence"]["sequence"]["metadata"]["name"] == "Flow Study Test"

    @pytest.mark.asyncio
    async def test_sequence_execution(self, sequence_manager):
        """Test sequence execution."""
        # Track sequence operations
        operations = []
        event = asyncio.Event()

        async def collect_operations(data: Dict[str, Any]) -> None:
            operations.append(data)
            event.set()

        await sequence_manager._message_broker.subscribe(
            "sequence/step",
            collect_operations
        )

        # Load test sequence first
        test_sequence = {
            "sequence": {
                "metadata": {
                    "name": "Flow Study Test",
                    "version": "1.0",
                    "created": "2024-03-20",
                    "author": "Test Author",
                    "description": "Test sequence for execution"
                },
                "steps": [
                    {
                        "name": "Initialize",
                        "action_group": "ready_system"
                    },
                    {
                        "name": "Test Pattern",
                        "action_group": "execute_pattern",
                        "parameters": {
                            "pattern_file": "test_pattern.yaml",
                            "parameter_file": "test_params.yaml",
                            "passes": 1
                        }
                    }
                ]
            }
        }

        # Save and load sequence
        sequence_path = Path("data/sequences/library/test_sequence.yaml")
        sequence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sequence_path, "w") as f:
            import yaml
            yaml.dump(test_sequence, f)

        await sequence_manager._message_broker.publish(
            "sequence/load",
            {"filename": "test_sequence.yaml"}
        )
        await asyncio.sleep(0.2)

        # Start sequence
        await sequence_manager._message_broker.publish(
            "sequence/start",
            {}
        )

        # Wait for step message or timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for sequence step message")

        # Verify execution
        assert len(operations) > 0
        assert operations[0]["step"]["name"] == "Initialize"

    @pytest.mark.asyncio
    async def test_sequence_state_transitions(self, sequence_manager):
        """Test sequence state transitions."""
        # Track state changes
        states = []
        event = asyncio.Event()

        async def collect_states(data: Dict[str, Any]) -> None:
            states.append(data)
            event.set()

        await sequence_manager._message_broker.subscribe(
            "sequence/status",
            collect_states
        )

        # Load test sequence first
        test_sequence = {
            "sequence": {
                "metadata": {
                    "name": "Flow Study Test",
                    "version": "1.0",
                    "created": "2024-03-20",
                    "author": "Test Author",
                    "description": "Test sequence for state transitions"
                },
                "steps": [
                    {
                        "name": "Initialize",
                        "action_group": "ready_system"
                    }
                ]
            }
        }

        # Save and load sequence
        sequence_path = Path("data/sequences/library/test_sequence.yaml")
        sequence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sequence_path, "w") as f:
            import yaml
            yaml.dump(test_sequence, f)

        await sequence_manager._message_broker.publish(
            "sequence/load",
            {"filename": "test_sequence.yaml"}
        )
        await asyncio.sleep(0.2)

        # Start sequence
        await sequence_manager._message_broker.publish(
            "sequence/start",
            {}
        )

        # Wait for state message or timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for sequence state message")

        # Verify state transitions
        assert len(states) > 0
        assert states[0]["state"] == "RUNNING"

    @pytest.mark.asyncio
    async def test_sequence_error_handling(self, sequence_manager):
        """Test sequence error handling."""
        # Track error messages
        errors = []
        event = asyncio.Event()

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)
            event.set()

        await sequence_manager._message_broker.subscribe(
            "sequence/error",
            collect_errors
        )

        # Try to start without loading sequence
        await sequence_manager._message_broker.publish(
            "sequence/start",
            {}
        )

        # Wait for error message or timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for sequence error message")

        # Verify error handling
        assert len(errors) > 0
        assert "No sequence loaded" in errors[0]["error"]
