# tests/test_monitors.py

import pytest
from unittest.mock import MagicMock, AsyncMock
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.components.monitors.process_monitor import ProcessMonitor
from micro_cold_spray.core.components.monitors.hardware_monitor import HardwareMonitor
from micro_cold_spray.core.components.monitors.state_monitor import StateMonitor
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
def tag_manager(config_manager, message_broker):
    return TagManager(config_manager, message_broker)

@pytest.fixture
def state_manager(message_broker, config_manager):
    return StateManager(message_broker, config_manager)

@pytest.fixture
def process_monitor(tag_manager, message_broker):
    return ProcessMonitor(tag_manager, message_broker)

@pytest.fixture
def hardware_monitor(tag_manager, message_broker):
    return HardwareMonitor(tag_manager, message_broker)

@pytest.fixture
def state_monitor(state_manager, tag_manager, config_manager):
    return StateMonitor(state_manager, tag_manager, config_manager)

def test_process_monitor_initialization(process_monitor):
    assert process_monitor is not None
    assert isinstance(process_monitor, ProcessMonitor)

def test_hardware_monitor_initialization(hardware_monitor):
    assert hardware_monitor is not None
    assert isinstance(hardware_monitor, HardwareMonitor)

def test_state_monitor_initialization(state_monitor):
    assert state_monitor is not None
    assert isinstance(state_monitor, StateMonitor)

@pytest.mark.asyncio
async def test_process_monitor_handle_status(process_monitor, message_broker, tag_manager):
    callback = MagicMock()
    message_broker.subscribe('process/status/updated', callback)
    await process_monitor._handle_process_status({'parameter': 'value'})
    callback.assert_called_once_with({
        'status': {'parameter': 'value'},
        'timestamp': tag_manager.get_tag("system.timestamp")
    })

@pytest.mark.asyncio
async def test_hardware_monitor_handle_status(hardware_monitor, message_broker, tag_manager):
    callback = MagicMock()
    message_broker.subscribe('hardware/status/updated', callback)
    await hardware_monitor._handle_hardware_status({'component': 'status'})
    callback.assert_called_once_with({
        'status': {'component': 'status'},
        'timestamp': tag_manager.get_tag("system.timestamp")
    })

@pytest.mark.asyncio
async def test_state_monitor_handle_state_change(state_monitor, message_broker, tag_manager):
    message = {
        'topic': 'state/change',
        'data': {'type': 'system', 'state': 'READY'}
    }
    await state_monitor.on_message(message)
    assert tag_manager.get_tag('system.state')['current'] == 'READY'