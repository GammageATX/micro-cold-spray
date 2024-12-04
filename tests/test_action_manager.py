# pytest tests/test_action_manager.py -v --asyncio-mode=auto

"""Action Manager test suite.

Tests action management according to .cursorrules:
- Action validation
- Action execution
- Action groups
- Error handling

Run with:
    pytest tests/test_action_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order
from micro_cold_spray.core.exceptions import OperationError


@order(TestOrder.OPERATIONS)
class TestActionManager:
    """Action management tests."""

    @pytest.mark.asyncio
    async def test_execute_atomic_motion_action(self, action_manager):
        """Test atomic motion action execution."""
        # Track messages
        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await action_manager._message_broker.subscribe("tag/set", collect_messages)

        # Mock validation response
        async def handle_validation(data: Dict[str, Any]) -> None:
            await action_manager._message_broker.publish(
                "tag/get/response",
                {
                    "tag": data["tag"],
                    "value": True,
                    "timestamp": datetime.now().isoformat()
                }
            )

        await action_manager._message_broker.subscribe("tag/get", handle_validation)

        # Execute action with position within stage dimensions
        await action_manager.execute_action("motion.move_xy", {
            "x": 100.0,  # Within 200mm stage dimension
            "y": 100.0   # Within 200mm stage dimension
        })
        await asyncio.sleep(0.1)

        # Verify results
        assert len(messages) > 0
        assert messages[0]["data"]["tag"] == "motion.motion_control.coordinated_move.xy_move.parameters.velocity"
        assert messages[2]["data"]["tag"] == "motion.motion_control.coordinated_move.xy_move.x_position"
        assert messages[2]["data"]["value"] == 100.0
        assert messages[3]["data"]["tag"] == "motion.motion_control.coordinated_move.xy_move.y_position"
        assert messages[3]["data"]["value"] == 100.0

    @pytest.mark.asyncio
    async def test_motion_limits_validation(self, action_manager):
        """Test motion limits validation against stage dimensions."""
        with pytest.raises(OperationError) as exc_info:
            await action_manager.execute_action("motion.move_xy", {
                "x": 250.0,  # Exceeds 200mm stage dimension
                "y": 100.0
            })
        assert "exceeds stage dimensions" in str(exc_info.value)
        assert "parameters" in exc_info.value.context
        assert exc_info.value.context["parameters"]["x"] == 250.0
