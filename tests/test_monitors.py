# tests/test_monitors.py

"""Monitor components test suite.

Run with:
    pytest tests/test_monitors.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from collections import defaultdict
from loguru import logger

from .test_tag_manager import (
    mock_plc_client,
    mock_ssh_client,
    tag_manager
)

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.components.monitors.process_monitor import ProcessMonitor
from micro_cold_spray.core.components.monitors.hardware_monitor import HardwareMonitor
from micro_cold_spray.core.components.monitors.state_monitor import StateMonitor
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.exceptions import MonitorError

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a clean MessageBroker instance."""
    broker = MessageBroker()
    broker._subscribers = defaultdict(set, {
        # Monitor topics
        "hardware/connection": set(),
        "hardware/status": set(),
        "hardware/error": set(),
        "process/status": set(),
        "process/error": set(),
        "state/change": set(),
        "state/error": set(),
        
        # Tag topics
        "tag/update": set(),
        
        # Error topics
        "error": set()
    })
    
    try:
        await broker.start()
        yield broker
    finally:
        await broker.shutdown()

@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[ConfigManager, None]:
    """Provide a ConfigManager instance with test configs."""
    config = ConfigManager(message_broker)
    config._configs['state'] = {
        'state': {
            'transitions': {
                'system': {
                    'INITIALIZING': ['READY', 'ERROR'],
                    'READY': ['RUNNING', 'ERROR'],
                    'RUNNING': ['STOPPED', 'ERROR'],
                    'STOPPED': ['READY', 'ERROR'],
                    'ERROR': ['INITIALIZING']
                }
            }
        }
    }
    try:
        yield config
    finally:
        await config.shutdown()

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
async def hardware_monitor(
    message_broker: MessageBroker,
    tag_manager: TagManager
) -> AsyncGenerator[HardwareMonitor, None]:
    """Provide a HardwareMonitor instance."""
    monitor = HardwareMonitor(
        message_broker=message_broker,  # Make sure this is first
        tag_manager=tag_manager
    )
    try:
        yield monitor
    finally:
        await monitor.stop()

@pytest.fixture
async def state_monitor(
    state_manager: StateManager,
    tag_manager: TagManager,
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> AsyncGenerator[StateMonitor, None]:
    """Provide a StateMonitor instance."""
    monitor = StateMonitor(
        state_manager=state_manager,
        tag_manager=tag_manager,
        message_broker=message_broker,
        config_manager=config_manager
    )
    try:
        yield monitor
    finally:
        await monitor.stop()

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
    """Test process status handling."""
    # Track status updates
    updates = []
    async def collect_updates(data: Dict[str, Any]) -> None:
        updates.append(data)
    await message_broker.subscribe("process/status/updated", collect_updates)
    
    # Send test status
    test_status = {'parameter': 'value'}
    await process_monitor._handle_process_status(test_status)
    await asyncio.sleep(0.1)
    
    assert len(updates) > 0
    assert "status" in updates[0]
    assert "timestamp" in updates[0]
    assert updates[0]["status"] == test_status  # Compare just the status part

@pytest.mark.asyncio
async def test_hardware_monitor_handle_status(hardware_monitor, message_broker, tag_manager):
    """Test hardware status handling."""
    updates = []
    async def collect_updates(data: Dict[str, Any]) -> None:
        updates.append(data)
    await message_broker.subscribe("hardware/status/updated", collect_updates)
    
    test_status = {'component': 'status'}
    await hardware_monitor._handle_hardware_status(test_status)
    await asyncio.sleep(0.1)
    
    assert len(updates) > 0
    assert updates[0]["status"] == test_status

@pytest.mark.asyncio
async def test_state_monitor_handle_state_change(state_monitor, message_broker, tag_manager):
    """Test state change handling."""
    updates = []
    async def collect_updates(data: Dict[str, Any]) -> None:
        updates.append(data)
    await message_broker.subscribe("state/change", collect_updates)
    
    test_state = {
        'type': 'system',
        'state': 'READY'
    }
    await state_monitor._handle_state_change(test_state)
    await asyncio.sleep(0.1)
    
    assert len(updates) > 0
    assert updates[0]["state"] == test_state["state"]