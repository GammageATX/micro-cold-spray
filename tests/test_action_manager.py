# pytest tests/test_action_manager.py -v --asyncio-mode=auto

"""Action Manager test suite.

Tests action execution according to process.yaml:
- Atomic action execution
- Action group execution
- Parameter substitution
- Action validation
- Error handling

Run with:
    pytest tests/test_action_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any, List
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order
from micro_cold_spray.core.exceptions import OperationError


@order(TestOrder.PROCESS)
class TestActionManager:
    """Action management tests."""

    @pytest.mark.asyncio
    async def test_execute_atomic_motion_action(self, action_manager):
        """Test atomic motion action execution."""
        # Track messages
        messages = []

        async def collect_messages(data: List[Any]) -> None:
            messages.extend(data)

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

        # Verify results - messages are [tag, value] pairs
        assert len(messages) > 0
        assert messages[0][0] == "motion.x.position"
        assert messages[0][1] == 100.0
        assert messages[1][0] == "motion.y.position"
        assert messages[1][1] == 100.0

    @pytest.mark.asyncio
    async def test_motion_limits_validation(self, action_manager):
        """Test motion limits validation against stage dimensions."""
        with pytest.raises(OperationError) as exc_info:
            await action_manager.execute_action("motion.move_xy", {
                "x": 250.0,  # Exceeds 200mm stage dimension
                "y": 100.0
            })
        assert "exceeds stage dimensions" in str(exc_info.value)
        assert "x" in exc_info.value.context
        assert exc_info.value.context["timestamp"]
