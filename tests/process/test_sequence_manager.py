"""Sequence Manager test suite.

Tests sequence management according to .cursorrules:
- Sequence validation
- Sequence execution
- Parameter substitution
- Error handling

Run with:
    pytest tests/operations/test_sequence_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
from pathlib import Path
from tests.conftest import TestOrder, order
from datetime import datetime

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.process.operations.actions.action_manager import ActionManager
from micro_cold_spray.core.process.operations.sequences.sequence_manager import SequenceManager


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
        action_manager=action_manager,
        sequence_path=Path("data/sequences")
    )
    yield manager


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
        sequence_path = Path("data/sequences/test_sequence.yaml")
        sequence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sequence_path, "w") as f:
            import yaml
            yaml.dump(test_sequence, f)

        # Load sequence
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-load-123",
                "request_type": "load",
                "filename": "test_sequence.yaml",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.2)

        # Start sequence
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-start-123",
                "request_type": "start",
                "timestamp": datetime.now().isoformat()
            }
        )

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
        sequence_path = Path("data/sequences/test_sequence.yaml")
        sequence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sequence_path, "w") as f:
            import yaml
            yaml.dump(test_sequence, f)

        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-load-123",
                "request_type": "load",
                "filename": "test_sequence.yaml",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.2)

        # Start sequence
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-start-123",
                "request_type": "start",
                "timestamp": datetime.now().isoformat()
            }
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
            "sequence/state",
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
        sequence_path = Path("data/sequences/test_sequence.yaml")
        sequence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sequence_path, "w") as f:
            import yaml
            yaml.dump(test_sequence, f)

        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-load-123",
                "request_type": "load",
                "filename": "test_sequence.yaml",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.2)

        # Start sequence
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-start-123",
                "request_type": "start",
                "timestamp": datetime.now().isoformat()
            }
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
            "sequence/request",
            {
                "request_id": "test-start-123",
                "request_type": "start",
                "timestamp": datetime.now().isoformat()
            }
        )

        # Wait for error message or timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for sequence error message")

        # Verify error handling
        assert len(errors) > 0
        assert "No sequence loaded" in errors[0]["error"]

    @pytest.mark.asyncio
    async def test_condition_validation(self, sequence_manager):
        """Test sequence condition validation."""
        # Track sequence messages
        messages = []
        event = asyncio.Event()

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
            event.set()

        await sequence_manager._message_broker.subscribe(
            "sequence/step",
            collect_messages
        )

        # Test sequence with conditions
        test_sequence = {
            "sequence": {
                "metadata": {
                    "name": "Condition Test",
                    "version": "1.0",
                    "created": "2024-03-20",
                    "author": "Test Author",
                    "description": "Test sequence for condition validation"
                },
                "steps": [
                    {
                        "name": "Wait for Vacuum",
                        "validation": {
                            "tag": "pressure.chamber_pressure",
                            "condition": "less_than",
                            "value": 5.0,
                            "timeout": 1.0
                        }
                    },
                    {
                        "name": "Start Gas Flow",
                        "action_group": "gas_control.set_main_flow",
                        "parameters": {
                            "flow_rate": 30.0
                        },
                        "validation": {
                            "tag": "gas_control.main_flow.measured",
                            "condition": "greater_than",
                            "value": 28.0,
                            "timeout": 1.0
                        }
                    }
                ]
            }
        }

        # Save and load sequence
        sequence_path = Path("data/sequences/test_sequence.yaml")
        sequence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sequence_path, "w") as f:
            import yaml
            yaml.dump(test_sequence, f)

        # Load sequence
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-load-123",
                "request_type": "load",
                "filename": "test_sequence.yaml",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Start sequence
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-start-123",
                "request_type": "start",
                "timestamp": datetime.now().isoformat()
            }
        )

        # Wait for step message or timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for sequence step message")

        # Verify validation messages
        assert len(messages) > 0
        assert any(m.get("state") == "IN_PROGRESS" and "Validating conditions" in m.get("message", "")
                   for m in messages)

    @pytest.mark.asyncio
    async def test_condition_timeout(self, sequence_manager):
        """Test condition validation timeout."""
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

        # Test sequence with condition that will timeout
        test_sequence = {
            "sequence": {
                "metadata": {
                    "name": "Timeout Test",
                    "version": "1.0",
                    "created": "2024-03-20",
                    "author": "Test Author",
                    "description": "Test sequence for timeout handling"
                },
                "steps": [
                    {
                        "name": "Wait for Impossible Condition",
                        "validation": {
                            "tag": "test.value",
                            "condition": "equals",
                            "value": 999999,  # Impossible value
                            "timeout": 0.5  # Short timeout
                        }
                    }
                ]
            }
        }

        # Save and load sequence
        sequence_path = Path("data/sequences/test_sequence.yaml")
        sequence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sequence_path, "w") as f:
            import yaml
            yaml.dump(test_sequence, f)

        # Load sequence
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-load-123",
                "request_type": "load",
                "filename": "test_sequence.yaml",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Start sequence
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-start-123",
                "request_type": "start",
                "timestamp": datetime.now().isoformat()
            }
        )

        # Wait for error message or timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for sequence error message")

        # Verify timeout error
        assert len(errors) > 0
        assert any("Timeout waiting for conditions" in e.get("error", "") for e in errors)

    @pytest.mark.asyncio
    async def test_multiple_conditions(self, sequence_manager):
        """Test multiple condition validation."""
        # Track step messages
        messages = []
        event = asyncio.Event()

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
            event.set()

        await sequence_manager._message_broker.subscribe(
            "sequence/step",
            collect_messages
        )

        # Test sequence with multiple conditions
        test_sequence = {
            "sequence": {
                "metadata": {
                    "name": "Multi-Condition Test",
                    "version": "1.0",
                    "created": "2024-03-20",
                    "author": "Test Author",
                    "description": "Test sequence for multiple conditions"
                },
                "steps": [
                    {
                        "name": "Check System State",
                        "validation": [
                            {
                                "tag": "pressure.chamber_pressure",
                                "condition": "less_than",
                                "value": 5.0,
                                "timeout": 1.0
                            },
                            {
                                "tag": "gas_control.main_flow.measured",
                                "condition": "equals",
                                "value": 0.0,
                                "timeout": 1.0
                            }
                        ]
                    }
                ]
            }
        }

        # Save and load sequence
        sequence_path = Path("data/sequences/test_sequence.yaml")
        sequence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sequence_path, "w") as f:
            import yaml
            yaml.dump(test_sequence, f)

        # Load sequence
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-load-123",
                "request_type": "load",
                "filename": "test_sequence.yaml",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Start sequence
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-start-123",
                "request_type": "start",
                "timestamp": datetime.now().isoformat()
            }
        )

        # Wait for step message or timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for sequence step message")

        # Verify validation messages
        assert len(messages) > 0
        assert any(m.get("state") == "IN_PROGRESS" and "Validating conditions" in m.get("message", "")
                   for m in messages)

    @pytest.mark.asyncio
    async def test_invalid_request_type(self, sequence_manager):
        """Test invalid request type."""
        # Test invalid request type
        await sequence_manager._message_broker.publish(
            "sequence/request",
            {
                "request_id": "test-invalid-123",
                "request_type": "invalid",
                "timestamp": datetime.now().isoformat()
            }
        )
