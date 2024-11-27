# tests/test_sequence_manager.py

import pytest
from unittest.mock import MagicMock, AsyncMock
from micro_cold_spray.core.components.operations.sequences.sequence_manager import SequenceManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.components.operations.actions.action_manager import ActionManager

@pytest.fixture
def message_broker():
    broker = MessageBroker()
    broker._subscribers = {}  # Reset subscribers for clean test environment
    return broker

@pytest.fixture
def config_manager(message_broker):
    return ConfigManager(message_broker)

@pytest.fixture
def tag_manager():
    return TagManager()

@pytest.fixture
def process_validator(message_broker):
    return ProcessValidator(message_broker)

@pytest.fixture
def action_manager():
    return ActionManager()

@pytest.fixture
def sequence_manager(config_manager, tag_manager, process_validator, action_manager):
    return SequenceManager(config_manager, tag_manager, process_validator, action_manager)

def test_sequence_manager_initialization(sequence_manager):
    assert sequence_manager is not None
    assert isinstance(sequence_manager, SequenceManager)

@pytest.mark.asyncio
async def test_sequence_manager_load_sequence(sequence_manager):
    sequence_name = "test_sequence"
    sequence_manager._sequences = {
        sequence_name: {
            "steps": [
                {"action": "move", "parameters": {"position": 10, "speed": 5}},
                {"action": "spray", "parameters": {"duration": 5, "pressure": 50}}
            ]
        }
    }
    await sequence_manager.load_sequence(sequence_name)
    assert sequence_manager.get_current_sequence() is not None

@pytest.mark.asyncio
async def test_sequence_manager_start_sequence(sequence_manager):
    sequence_name = "test_sequence"
    sequence_manager._sequences = {
        sequence_name: {
            "steps": [
                {"action": "move", "parameters": {"position": 10, "speed": 5}},
                {"action": "spray", "parameters": {"duration": 5, "pressure": 50}}
            ]
        }
    }
    await sequence_manager.load_sequence(sequence_name)
    await sequence_manager.start_sequence()
    assert sequence_manager.get_current_step() == 2