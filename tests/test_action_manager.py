# tests/test_action_manager.py

import pytest
from unittest.mock import MagicMock, AsyncMock
from micro_cold_spray.core.components.operations.actions.action_manager import ActionManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.hardware.controllers.motion_controller import MotionController
from micro_cold_spray.core.hardware.controllers.equipment_controller import EquipmentController
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator

@pytest.fixture
def message_broker():
    broker = MessageBroker()
    broker._subscribers = {}  # Reset subscribers for clean test environment
    return broker

@pytest.fixture
def config_manager(message_broker):
    return ConfigManager(message_broker)

@pytest.fixture
def tag_manager(config_manager, message_broker):
    return TagManager(config_manager, message_broker)

@pytest.fixture
def motion_controller():
    return MotionController()

@pytest.fixture
def equipment_controller():
    return EquipmentController()

@pytest.fixture
def process_validator(message_broker, config_manager):
    return ProcessValidator(message_broker, config_manager)

@pytest.fixture
def action_manager(config_manager, tag_manager, motion_controller, equipment_controller, process_validator):
    return ActionManager(config_manager, tag_manager, motion_controller, equipment_controller, process_validator)

def test_action_manager_initialization(action_manager):
    assert action_manager is not None
    assert isinstance(action_manager, ActionManager)

@pytest.mark.asyncio
async def test_action_manager_execute_move(action_manager):
    parameters = {"position": 10, "speed": 5}
    action_manager._motion.move_to = AsyncMock()
    await action_manager.execute_action("move", parameters)
    action_manager._motion.move_to.assert_called_once_with(10, 5)

@pytest.mark.asyncio
async def test_action_manager_execute_spray(action_manager):
    parameters = {"duration": 5, "pressure": 50}
    action_manager._equipment.set_pressure = AsyncMock()
    action_manager._equipment.start_spray = AsyncMock()
    action_manager._equipment.stop_spray = AsyncMock()
    await action_manager.execute_action("spray", parameters)
    action_manager._equipment.set_pressure.assert_called_once_with(50)
    action_manager._equipment.start_spray.assert_called_once()
    action_manager._equipment.stop_spray.assert_called_once()