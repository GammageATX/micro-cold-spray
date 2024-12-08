"""State Manager test suite.

Tests state management functionality:
- State transitions
- State validation
- Error handling
- State change propagation

Run with:
    pytest tests/infrastructure/test_state_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order

from micro_cold_spray.core.infrastructure.state.state_manager import StateManager


@pytest.fixture
async def state_manager(message_broker, config_manager) -> AsyncGenerator[StateManager, None]:
    """Create state manager with mocked dependencies."""
    manager = StateManager(
        message_broker=message_broker,
        config_manager=config_manager
    )
    await manager.initialize()

    # Set required conditions for transitions
    await message_broker.publish("tag/update", {
        "tag": "hardware.plc.connected",
        "value": True
    })
    await message_broker.publish("tag/update", {
        "tag": "hardware.motion.connected",
        "value": True
    })
    await message_broker.publish("tag/update", {
        "tag": "hardware.plc.enabled",
        "value": True
    })
    await message_broker.publish("tag/update", {
        "tag": "hardware.motion.enabled",
        "value": True
    })
    await asyncio.sleep(0.1)  # Wait for conditions to update

    yield manager
    await manager.shutdown()


@order(TestOrder.INFRASTRUCTURE)
class TestStateManager:
    """State Manager tests run with infrastructure."""

    @pytest.mark.asyncio
    async def test_state_request_change(self, state_manager):
        """Test state change request/response pattern."""
        responses = []
        changes = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        async def collect_changes(data: Dict[str, Any]) -> None:
            changes.append(data)

        await state_manager._message_broker.subscribe("state/response", collect_responses)
        await state_manager._message_broker.subscribe("state/change", collect_changes)

        # Request valid transition
        await state_manager._message_broker.publish(
            "state/request",
            {
                "request_type": "change",
                "state": "READY",
                "request_id": "test-123",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Verify response
        assert len(responses) == 1
        assert responses[0]["request_id"] == "test-123"
        assert responses[0]["success"] is True
        assert responses[0]["state"] == "READY"
        assert responses[0]["previous"] == "INITIALIZING"
        assert "timestamp" in responses[0]

        # Verify state change notification
        assert len(changes) == 1
        assert changes[0]["state"] == "READY"
        assert changes[0]["previous"] == "INITIALIZING"
        assert "description" in changes[0]
        assert "timestamp" in changes[0]

    @pytest.mark.asyncio
    async def test_state_request_get(self, state_manager):
        """Test state get request/response pattern."""
        responses = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        await state_manager._message_broker.subscribe("state/response", collect_responses)

        # Send get request
        await state_manager._message_broker.publish(
            "state/request",
            {
                "request_type": "get",
                "state": "current",  # Value doesn't matter for get
                "request_id": "test-456",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Verify response
        assert len(responses) == 1
        assert responses[0]["request_id"] == "test-456"
        assert responses[0]["success"] is True
        assert "state" in responses[0]
        assert "previous" in responses[0]
        assert "conditions" in responses[0]
        assert "valid_transitions" in responses[0]
        assert "timestamp" in responses[0]

    @pytest.mark.asyncio
    async def test_invalid_state_request(self, state_manager):
        """Test invalid state request handling."""
        errors = []
        responses = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        await state_manager._message_broker.subscribe("error", collect_errors)
        await state_manager._message_broker.subscribe("state/response", collect_responses)

        # Request invalid state
        await state_manager._message_broker.publish(
            "state/request",
            {
                "request_type": "change",
                "state": "INVALID_STATE",
                "request_id": "test-789",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Verify error
        assert len(errors) == 1
        assert errors[0]["source"] == "state_manager"
        assert "Invalid state requested" in errors[0]["error"]
        assert errors[0]["request_id"] == "test-789"
        assert "timestamp" in errors[0]

    @pytest.mark.asyncio
    async def test_invalid_transition_request(self, state_manager):
        """Test invalid transition request handling."""
        errors = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        await state_manager._message_broker.subscribe("error", collect_errors)

        # Request invalid transition (INITIALIZING -> RUNNING)
        await state_manager._message_broker.publish(
            "state/request",
            {
                "request_type": "change",
                "state": "RUNNING",
                "request_id": "test-abc",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Verify error
        assert len(errors) == 1
        assert errors[0]["source"] == "state_manager"
        assert "Invalid state transition" in errors[0]["error"]
        assert errors[0]["request_id"] == "test-abc"
        assert "timestamp" in errors[0]

    @pytest.mark.asyncio
    async def test_unmet_conditions_request(self, state_manager):
        """Test state request with unmet conditions."""
        errors = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        await state_manager._message_broker.subscribe("error", collect_errors)

        # Disable hardware
        await state_manager._message_broker.publish("tag/update", {
            "tag": "hardware.plc.enabled",
            "value": False
        })
        await asyncio.sleep(0.1)

        # Request state that requires enabled hardware
        await state_manager._message_broker.publish(
            "state/request",
            {
                "request_type": "change",
                "state": "READY",
                "request_id": "test-def",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Verify error
        assert len(errors) == 1
        assert errors[0]["source"] == "state_manager"
        assert "Required conditions not met" in errors[0]["error"]
        assert errors[0]["request_id"] == "test-def"
        assert "timestamp" in errors[0]

    @pytest.mark.asyncio
    async def test_error_state_transition(self, state_manager):
        """Test transition to error state."""
        changes = []
        responses = []

        async def collect_changes(data: Dict[str, Any]) -> None:
            changes.append(data)

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        await state_manager._message_broker.subscribe("state/change", collect_changes)
        await state_manager._message_broker.subscribe("state/response", collect_responses)

        # First transition to READY
        await state_manager._message_broker.publish(
            "state/request",
            {
                "request_type": "change",
                "state": "READY",
                "request_id": "test-ghi",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Then transition to ERROR with error info
        await state_manager._message_broker.publish(
            "state/request",
            {
                "request_type": "change",
                "state": "ERROR",
                "error": "Test error condition",
                "request_id": "test-jkl",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Verify changes
        assert len(changes) == 2
        assert changes[1]["state"] == "ERROR"
        assert changes[1]["error"] == "Test error condition"
        assert "timestamp" in changes[1]

        # Verify responses
        assert len(responses) == 2
        assert responses[1]["success"] is True
        assert responses[1]["state"] == "ERROR"
        assert responses[1]["request_id"] == "test-jkl"
        assert "timestamp" in responses[1]
