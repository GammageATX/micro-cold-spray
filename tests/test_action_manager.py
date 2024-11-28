"""Action Manager test suite.

Tests action management according to operation.yaml:
- Standard actions from operation.yaml
- Action validation and execution
- Action sequence management
- Message pattern compliance
- Error handling

Standard Actions (from operation.yaml):
- Motion actions (move_to_trough, move_to_home)
- Gas actions (start_gas_flow, stop_gas_flow)
- Powder actions (start_powder_feed, stop_powder_feed)
- Shutter actions (engage_shutter, disengage_shutter)
- System actions (prepare_system, cleanup_system)

Message Patterns:
- Must use "action/execute" for action requests
- Must use "action/status" for status updates
- Must use "action/complete" for completion
- Must use "action/error" for errors
- Must include timestamps

Run with:
    pytest tests/test_action_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from tests.conftest import TestOrder

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.operations.actions.action_manager import ActionManager
from micro_cold_spray.core.exceptions import OperationError
from tests.conftest import TestOrder

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a MessageBroker instance."""
    broker = MessageBroker()
    broker._subscribers = {
        # Action topics
        "action/execute": set(),
        "action/status": set(),  # Added status topic
        "action/complete": set(), # Added completion topic
        "action/error": set(),    # Added error topic
        
        # Required topics
        "tag/set": set(),
        "tag/get": set(),
        "tag/get/response": set(),
        "state/change": set(),
        "error": set()
    }

@TestOrder.PROCESS
class TestActionManager:
    """Action management tests run after pattern manager."""
    
    @pytest.mark.asyncio
    async def test_action_manager_initialization(self, action_manager):
        """Test action manager initialization."""
        assert action_manager._is_initialized
        operation_config = action_manager._config_manager.get_config('operation')
        assert 'actions' in operation_config
        assert 'standard_actions' in operation_config['actions']

    @pytest.mark.asyncio
    async def test_action_manager_move_to_trough(self, action_manager):
        """Test move_to_trough action from operation.yaml."""
        # Track tag operations
        operations = []
        async def collect_operations(data: Dict[str, Any]) -> None:
            operations.append(data)
        await action_manager._message_broker.subscribe("tag/set", collect_operations)
        
        # Execute move_to_trough action
        await action_manager.execute_action("move_to_trough", {})
        await asyncio.sleep(0.1)
        
        # Verify operation sequence from operation.yaml
        assert len(operations) >= 3  # move_to_safe_z, move_xy_to_trough, move_to_collection_height
        operation_sequence = [op.get("tag") for op in operations]
        assert "motion.z.target" in operation_sequence  # move_to_safe_z
        assert "motion.xy.target" in operation_sequence  # move_xy_to_trough
        assert all("timestamp" in op for op in operations)

    @pytest.mark.asyncio
    async def test_action_manager_start_gas_flow(self, action_manager):
        """Test start_gas_flow action from operation.yaml."""
        # Track tag operations
        operations = []
        async def collect_operations(data: Dict[str, Any]) -> None:
            operations.append(data)
        await action_manager._message_broker.subscribe("tag/set", collect_operations)
        
        # Execute start_gas_flow action
        await action_manager.execute_action("start_gas_flow", {
            "main_flow": 50.0
        })
        await asyncio.sleep(0.1)
        
        # Verify operation sequence from operation.yaml
        assert len(operations) >= 2  # open_main_valve, set_main_flow
        operation_sequence = [op.get("tag") for op in operations]
        assert "valve.main.state" in operation_sequence  # open_main_valve
        assert "gas.main.flow" in operation_sequence  # set_main_flow
        assert all("timestamp" in op for op in operations)

    @pytest.mark.asyncio
    async def test_action_manager_prepare_system(self, action_manager):
        """Test prepare_system action from operation.yaml."""
        # Track operations and state changes
        operations = []
        async def collect_operations(data: Dict[str, Any]) -> None:
            operations.append(data)
        
        await action_manager._message_broker.subscribe("tag/set", collect_operations)
        await action_manager._message_broker.subscribe("state/change", collect_operations)
        
        # Execute prepare_system action
        await action_manager.execute_action("prepare_system", {})
        await asyncio.sleep(0.1)
        
        # Verify operation sequence from operation.yaml
        assert len(operations) > 0
        operation_sequence = [op.get("tag", op.get("state")) for op in operations]
        assert any("vacuum" in str(op) for op in operation_sequence)  # verify_vacuum
        assert any("gas" in str(op) for op in operation_sequence)  # verify_gas_supply
        assert all("timestamp" in op for op in operations)