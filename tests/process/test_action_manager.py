# pytest tests/test_action_manager.py -v --asyncio-mode=auto

"""Action Manager test suite.

Tests action management according to .cursorrules:
- Action validation
- Action execution
- Action groups
- Error handling

Run with:
    pytest tests/operations/test_action_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any
import asyncio
from tests.conftest import TestOrder, order
from micro_cold_spray.core.process.operations.actions.action_manager import ActionManager


@order(TestOrder.OPERATIONS)
class TestActionManager:
    """Action management tests."""

    @pytest.mark.asyncio
    async def test_atomic_action_request(self, action_manager):
        """Test atomic action request/response pattern."""
        # Track messages
        responses = []
        states = []
        tag_requests = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        async def collect_states(data: Dict[str, Any]) -> None:
            states.append(data)

        async def collect_tag_requests(data: Dict[str, Any]) -> None:
            tag_requests.append(data)

        await action_manager._message_broker.subscribe("action/response", collect_responses)
        await action_manager._message_broker.subscribe("action/state", collect_states)
        await action_manager._message_broker.subscribe("tag/request", collect_tag_requests)

        # Send action request
        await action_manager._message_broker.publish(
            "action/request",
            {
                "request_type": "execute",
                "action": "shutter.control_shutter",
                "parameters": {
                    "value": True
                },
                "request_id": "test-123"
            }
        )
        await asyncio.sleep(0.1)

        # Verify shutter tag was requested
        assert len(tag_requests) == 1
        assert tag_requests[0]["tags"][0]["tag"] == "relay_control.shutter"
        assert tag_requests[0]["tags"][0]["value"] is True
        
        # Verify state updates
        assert len(states) >= 2
        assert states[0]["state"] == "EXECUTING"
        assert states[-1]["state"] == "COMPLETED"
        
        # Verify response
        assert len(responses) == 1
        assert responses[0]["success"] is True
        assert responses[0]["request_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_action_group_request(self, action_manager):
        """Test action group request/response pattern."""
        # Track messages
        responses = []
        states = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        async def collect_states(data: Dict[str, Any]) -> None:
            states.append(data)

        await action_manager._message_broker.subscribe("action/group/response", collect_responses)
        await action_manager._message_broker.subscribe("action/group/state", collect_states)

        # Send group request
        await action_manager._message_broker.publish(
            "action/group/request",
            {
                "request_type": "execute",
                "group": "ready_system",
                "parameters": {},
                "request_id": "test-456"
            }
        )
        await asyncio.sleep(0.1)

        # Verify response
        assert len(responses) == 1
        assert responses[0]["request_id"] == "test-456"
        assert responses[0]["success"] is True
        
        # Verify state updates
        assert len(states) >= 3  # Initial, progress, completed
        assert states[0]["state"] == "EXECUTING"
        assert states[0]["progress"] == 0
        assert states[-1]["state"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_action_validation(self, action_manager):
        """Test action parameter validation."""
        # Track error messages
        errors = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        await action_manager._message_broker.subscribe("error", collect_errors)

        # Send invalid action request
        await action_manager._message_broker.publish(
            "action/request",
            {
                "request_type": "execute",
                "action": "motion.move_xy",
                "parameters": {
                    "x": 250.0,  # Exceeds stage dimensions
                    "y": 100.0
                },
                "request_id": "test-789"
            }
        )
        await asyncio.sleep(0.1)

        # Verify error response
        assert len(errors) >= 1
        assert any(e["source"] == "action_manager" for e in errors)
        assert any("stage dimensions" in str(e.get("error", "")) for e in errors)

    @pytest.fixture
    async def action_manager(self, message_broker, config_manager, process_validator):
        """Create action manager instance."""
        manager = ActionManager(message_broker, config_manager, process_validator)
        await manager.initialize()
        return manager

    @pytest.mark.asyncio
    async def test_ready_system_action_group(self, action_manager):
        """Test ready system action group."""
        # Track messages
        responses = []
        states = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        async def collect_states(data: Dict[str, Any]) -> None:
            states.append(data)

        await action_manager._message_broker.subscribe("action/group/response", collect_responses)
        await action_manager._message_broker.subscribe("action/group/state", collect_states)

        # Send action group request
        await action_manager._message_broker.publish("action/group/request", {
            "request_type": "execute",
            "group": "ready_system",
            "parameters": {},
            "request_id": "test-123"
        })
        
        await asyncio.sleep(0.1)  # Allow time for processing
        
        # Verify response indicates success
        assert len(responses) == 1
        assert responses[0]["request_id"] == "test-123"
        assert responses[0]["success"] is True
        
        # Verify state updates
        assert len(states) >= 3  # Initial, progress, completed
        assert states[0]["state"] == "EXECUTING"
        assert states[0]["progress"] == 0
        assert states[-1]["state"] == "COMPLETED"
