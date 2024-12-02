"""State Manager test suite.

Tests state management functionality:
- State transitions
- State validation
- Error handling
- State change propagation

Run with:
    pytest tests/test_state_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
from tests.conftest import TestOrder, order

from micro_cold_spray.core.infrastructure.state.state_manager import StateManager


@pytest.fixture
async def state_manager(message_broker, config_manager) -> AsyncGenerator[StateManager, None]:
    """Create state manager with mocked dependencies."""
    # Mock state config
    config_manager._configs['state'] = {
        'states': {
            'IDLE': {
                'transitions': ['READY']
            },
            'READY': {
                'transitions': ['RUNNING', 'IDLE']
            },
            'RUNNING': {
                'transitions': ['READY', 'ERROR']
            },
            'ERROR': {
                'transitions': ['IDLE']
            }
        },
        'initial': 'IDLE'
    }

    manager = StateManager(
        message_broker=message_broker,
        config_manager=config_manager
    )
    await manager.initialize()
    yield manager
    await manager.shutdown()


@order(TestOrder.INFRASTRUCTURE)
class TestStateManager:
    """State Manager tests run with infrastructure."""

    @pytest.mark.asyncio
    async def test_valid_transition(self, state_manager):
        """Test valid state transition."""
        # Track state changes
        changes = []

        async def collect_changes(data: Dict[str, Any]) -> None:
            changes.append(data)

        await state_manager._message_broker.subscribe("state/change", collect_changes)

        # Request valid transition
        await state_manager._message_broker.publish(
            "state/request",
            {"state": "READY"}
        )
        await asyncio.sleep(0.1)

        assert len(changes) == 1
        assert changes[0]["state"] == "READY"
        assert changes[0]["previous"] == "IDLE"

    @pytest.mark.asyncio
    async def test_invalid_transition(self, state_manager):
        """Test invalid state transition."""
        # Track state changes
        changes = []

        async def collect_changes(data: Dict[str, Any]) -> None:
            changes.append(data)

        await state_manager._message_broker.subscribe("state/change", collect_changes)

        # Request invalid transition
        await state_manager._message_broker.publish(
            "state/request",
            {"state": "RUNNING"}  # Can't go directly to RUNNING from IDLE
        )
        await asyncio.sleep(0.1)

        assert len(changes) == 0  # No state change should occur

    @pytest.mark.asyncio
    async def test_error_transition(self, state_manager):
        """Test transition to error state."""
        # Track state changes
        changes = []

        async def collect_changes(data: Dict[str, Any]) -> None:
            changes.append(data)

        await state_manager._message_broker.subscribe("state/change", collect_changes)

        # Move to READY then RUNNING
        await state_manager._message_broker.publish(
            "state/request",
            {"state": "READY"}
        )
        await asyncio.sleep(0.1)
        await state_manager._message_broker.publish(
            "state/request",
            {"state": "RUNNING"}
        )
        await asyncio.sleep(0.1)

        # Trigger error transition
        await state_manager._message_broker.publish(
            "state/request",
            {"state": "ERROR", "error": "Test error"}
        )
        await asyncio.sleep(0.1)

        assert len(changes) == 3
        assert changes[-1]["state"] == "ERROR"
        assert "error" in changes[-1]

    @pytest.mark.asyncio
    async def test_invalid_state(self, state_manager):
        """Test invalid state handling."""
        # Track error messages
        errors = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        await state_manager._message_broker.subscribe("error", collect_errors)

        # Request invalid state
        await state_manager._message_broker.publish(
            "state/request",
            {"state": "INVALID"}
        )
        await asyncio.sleep(0.1)

        assert len(errors) == 1
        assert "Invalid state" in str(errors[0]["error"])
        assert errors[0]["topic"] == "state/transition"
