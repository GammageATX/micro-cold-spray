# tests/test_state_manager.py

"""State Manager test suite.

Run with:
    pytest tests/test_state_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock
import asyncio
from datetime import datetime
from collections import defaultdict

from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a clean MessageBroker instance."""
    broker = MessageBroker()
    broker._subscribers = defaultdict(set, {
        # State topics
        "state/request": set(),
        "state/change": set(),
        "state/error": set(),
        "state/transition": set(),
        
        # Config topics
        "config/update/state": set(),
        "config/update/*": set(),
        
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
    """Provide a ConfigManager instance with test state config."""
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
async def state_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> AsyncGenerator[StateManager, None]:
    """Provide a StateManager instance."""
    manager = StateManager(message_broker, config_manager)
    try:
        await manager.start()
        yield manager
    finally:
        await manager.shutdown()

@pytest.mark.asyncio
async def test_state_manager_initialization(state_manager: StateManager) -> None:
    """Test StateManager initializes correctly."""
    assert await state_manager.get_current_state() == "INITIALIZING"
    assert await state_manager.get_previous_state() == ""
    assert state_manager._message_broker is not None
    assert state_manager._config_manager is not None

@pytest.mark.asyncio
async def test_state_manager_valid_transition(state_manager: StateManager) -> None:
    """Test valid state transition."""
    # INITIALIZING -> READY -> RUNNING
    await state_manager.set_state("READY")
    assert await state_manager.get_current_state() == "READY"
    assert await state_manager.get_previous_state() == "INITIALIZING"
    
    await state_manager.set_state("RUNNING")
    assert await state_manager.get_current_state() == "RUNNING"
    assert await state_manager.get_previous_state() == "READY"

@pytest.mark.asyncio
async def test_state_manager_invalid_transition(state_manager: StateManager) -> None:
    """Test invalid state transition is rejected."""
    initial_state = await state_manager.get_current_state()
    assert initial_state == "INITIALIZING"
    
    # Try invalid transition (INITIALIZING -> RUNNING)
    await state_manager.set_state("RUNNING")
    
    # State should not change
    assert await state_manager.get_current_state() == "INITIALIZING"
    assert await state_manager.get_previous_state() == ""

@pytest.mark.asyncio
async def test_state_manager_error_transition(state_manager: StateManager) -> None:
    """Test transition to error state."""
    # Any state can transition to ERROR
    await state_manager.set_state("ERROR")
    assert await state_manager.get_current_state() == "ERROR"
    assert await state_manager.get_previous_state() == "INITIALIZING"
    
    # ERROR can only transition to INITIALIZING
    await state_manager.set_state("INITIALIZING")
    assert await state_manager.get_current_state() == "INITIALIZING"
    assert await state_manager.get_previous_state() == "ERROR"

@pytest.mark.asyncio
async def test_state_manager_state_change_event(
    state_manager: StateManager,
    message_broker: MessageBroker
) -> None:
    """Test state change events are published."""
    # Track state change events
    events = []
    async def collect_events(data: Dict[str, Any]) -> None:
        events.append(data)
    await message_broker.subscribe("state/change", collect_events)
    
    # Make state transition
    await state_manager.set_state("READY")
    await asyncio.sleep(0.1)  # Allow time for event processing
    
    # Verify event was published
    assert len(events) > 0
    event = events[0]
    assert event["previous_state"] == "INITIALIZING"
    assert event["current_state"] == "READY"
    assert "timestamp" in event

@pytest.mark.asyncio
async def test_state_manager_config_update(
    state_manager: StateManager,
    message_broker: MessageBroker
) -> None:
    """Test state manager handles config updates."""
    # Update state config
    new_config = {
        'state': {
            'transitions': {
                'system': {
                    'INITIALIZING': ['TEST_STATE'],
                    'TEST_STATE': ['INITIALIZING']
                }
            }
        }
    }
    await message_broker.publish("config/update/state", new_config)
    await asyncio.sleep(0.1)  # Allow time for update
    
    # Try new transition
    await state_manager.set_state("TEST_STATE")
    assert await state_manager.get_current_state() == "TEST_STATE"
    assert await state_manager.get_previous_state() == "INITIALIZING"

@pytest.mark.asyncio
async def test_state_manager_error_handling(
    state_manager: StateManager,
    message_broker: MessageBroker
) -> None:
    """Test error handling during state operations."""
    # Track errors
    errors = []
    async def collect_errors(data: Dict[str, Any]) -> None:
        errors.append(data)
    await message_broker.subscribe("error", collect_errors)
    
    # Try invalid state
    await state_manager.set_state("INVALID_STATE")
    await asyncio.sleep(0.1)  # Allow time for error handling
    
    # Verify error was published
    assert len(errors) > 0
    error = errors[0]
    assert "error" in error
    assert "state" in error["topic"]
    
    # State should not have changed
    assert await state_manager.get_current_state() == "INITIALIZING"