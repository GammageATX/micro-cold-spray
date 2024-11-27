# tests/test_state_manager.py

import pytest
from unittest.mock import MagicMock
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager

@pytest.fixture
def message_broker():
    broker = MessageBroker()
    broker._subscribers = {}  # Reset subscribers for clean test environment
    return broker

@pytest.fixture
def config_manager(message_broker):
    config_manager = ConfigManager(message_broker)
    config_manager._configs = {
        'state': {
            'state': {
                'transitions': {
                    'system': {
                        'INITIALIZING': ['READY'],
                        'READY': ['RUNNING', 'ERROR'],
                        'RUNNING': ['STOPPED', 'ERROR'],
                        'STOPPED': ['READY'],
                        'ERROR': ['INITIALIZING']
                    }
                }
            }
        }
    }
    return config_manager

@pytest.fixture
def state_manager(message_broker, config_manager):
    return StateManager(message_broker, config_manager)

def test_state_manager_initialization(state_manager):
    assert state_manager is not None
    assert isinstance(state_manager, StateManager)

@pytest.mark.asyncio
async def test_state_manager_set_get_state(state_manager, message_broker):
    await state_manager.start()
    # Assuming there's a method to get the current state
    current_state = await state_manager.get_current_state()
    assert current_state == "INITIALIZING"

@pytest.mark.asyncio
async def test_state_manager_invalid_transition(state_manager, message_broker):
    await state_manager.start()
    # Assuming there's a method to set the state
    await state_manager.set_state("READY")
    await state_manager.set_state("INITIALIZING")  # Invalid transition
    current_state = await state_manager.get_current_state()
    assert current_state == "READY"  # State should not change

@pytest.mark.asyncio
async def test_state_manager_valid_transition(state_manager, message_broker):
    await state_manager.start()
    await state_manager.set_state("READY")
    await state_manager.set_state("RUNNING")  # Valid transition
    current_state = await state_manager.get_current_state()
    assert current_state == "RUNNING"

@pytest.mark.asyncio
async def test_state_manager_config_update(state_manager, message_broker):
    new_config = {
        'config': {
            'state': {
                'transitions': {
                    'system': {
                        'INITIALIZING': ['READY'],
                        'READY': ['RUNNING', 'ERROR'],
                        'RUNNING': ['STOPPED', 'ERROR'],
                        'STOPPED': ['READY'],
                        'ERROR': ['INITIALIZING']
                    }
                }
            }
        }
    }
    await state_manager._handle_config_update(new_config)
    assert state_manager._state_config == new_config['config']

@pytest.mark.asyncio
async def test_state_manager_handle_state_request(state_manager, message_broker):
    request_data = {"requested_state": "READY"}
    await state_manager._handle_state_request(request_data)
    current_state = await state_manager.get_current_state()
    assert current_state == "READY"