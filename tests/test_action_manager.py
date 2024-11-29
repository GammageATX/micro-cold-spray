"""Action Manager test suite.

Tests action management according to process.yaml:
- Atomic actions execution
- Action group orchestration
- Parameter substitution
- Message pattern compliance
- Error handling

Run with:
    pytest tests/test_action_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order

@order(TestOrder.PROCESS)
class TestActionManager:
    """Action management tests."""
    
    @pytest.mark.asyncio
    async def test_execute_atomic_motion_action(self, action_manager):
        """Test atomic motion action execution."""
        # Track tag operations
        operations = []
        async def collect_operations(data: Dict[str, Any]) -> None:
            operations.append(data)
        await action_manager._message_broker.subscribe("tag/set", collect_operations)
        
        # Mock tag response for validation
        async def handle_tag_request(data: Dict[str, Any]) -> None:
            await action_manager._message_broker.publish(
                "tag/get/response",
                {
                    "tag": data["tag"],
                    "value": 100.0,  # Mock value
                    "timestamp": datetime.now().isoformat()
                }
            )
        await action_manager._message_broker.subscribe("tag/get", handle_tag_request)
        
        # Execute move_xy action
        await action_manager.execute_action("motion.move_xy", {
            "x": 100.0,
            "y": 100.0,
            "velocity": 50.0
        })
        await asyncio.sleep(0.1)
        
        # Verify correct tag messages sent
        assert len(operations[0]) >= 3  # All required motion parameters
        assert any("xy_move.x_position" in str(tag["tag"]) for tag in operations[0])
        assert any("xy_move.y_position" in str(tag["tag"]) for tag in operations[0])
        assert any("xy_move.parameters.velocity" in str(tag["tag"]) for tag in operations[0])

    @pytest.mark.asyncio
    async def test_execute_action_group(self, action_manager):
        """Test action group execution."""
        # Track operations
        operations = []
        async def collect_operations(data: Dict[str, Any]) -> None:
            operations.append(data)
        await action_manager._message_broker.subscribe("tag/set", collect_operations)
        
        # Mock tag response for validation
        async def handle_tag_request(data: Dict[str, Any]) -> None:
            await action_manager._message_broker.publish(
                "tag/get/response",
                {
                    "tag": data["tag"],
                    "value": True,  # Mock value
                    "timestamp": datetime.now().isoformat()
                }
            )
        await action_manager._message_broker.subscribe("tag/get", handle_tag_request)
        
        # Execute ready_system action group
        await action_manager.execute_action_group("ready_system", {})
        await asyncio.sleep(0.1)
        
        # Verify action sequence
        assert len(operations) > 0
        operation_tags = [tag["tag"] for tag in operations[0]]
        assert any("motion.motion_control.coordinated_move.xy_move" in tag for tag in operation_tags)
        assert any("parameters.velocity" in tag for tag in operation_tags)
        assert any("x_position" in tag for tag in operation_tags)
        assert any("y_position" in tag for tag in operation_tags)

    @pytest.mark.asyncio
    async def test_parameter_substitution(self, action_manager):
        """Test parameter substitution in actions."""
        # Track operations
        operations = []
        async def collect_operations(data: Dict[str, Any]) -> None:
            operations.append(data)
        await action_manager._message_broker.subscribe("tag/set", collect_operations)
        
        # Mock tag response for validation
        async def handle_tag_request(data: Dict[str, Any]) -> None:
            await action_manager._message_broker.publish(
                "tag/get/response",
                {
                    "tag": data["tag"],
                    "value": 50.0,  # Match expected value
                    "timestamp": datetime.now().isoformat()
                }
            )
        await action_manager._message_broker.subscribe("tag/get", handle_tag_request)
        
        # Execute action with parameter substitution
        parameters = {
            "gas": {
                "main_flow": 50.0
            }
        }
        await action_manager.execute_action("gas.set_main_flow", parameters)
        await asyncio.sleep(0.1)
        
        # Verify parameter substitution
        assert len(operations) > 0
        assert any(
            tag["tag"] == "gas_control.main_flow.setpoint" and
            tag["value"] == 50.0
            for tag in operations[0]
        )