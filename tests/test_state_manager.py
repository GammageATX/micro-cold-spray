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
    # Track current state for tests
    state_data = {
        "current_state": "INITIALIZING",
        "previous_state": ""
    }
    
    broker._subscribers = defaultdict(set, {
        # State topics
        "state/request": set(),
        "state/change": set(),
        "state/error": set(),
        "state/transition": set(),
        "state/set": set(),
        
        # Config topics
        "config/update/state": set(),
        "config/update/*": set(),
        
        # Tag topics
        "tag/set": set(),
        "tag/get": set(),
        "tag/get/response": set(),
        "tag/update": set(),
        
        # Error topics
        "error": set(),
        
        # System topics
        "system/state": set(),
        "system/state/change": set(),
        "system_state.state": set(),
        "system_state.previous_state": set()
    })
    
    try:
        await broker.start()
        
        # Set up tag get handler
        async def tag_get_handler(data: Dict[str, Any]) -> None:
            """Handle tag get requests."""
            tag = data.get("tag")
            
            if tag == "system_state.state":
                await broker.publish(
                    "tag/get/response",
                    {
                        "tag": tag,
                        "value": state_data["current_state"]
                    }
                )
            elif tag == "system_state.previous_state":
                await broker.publish(
                    "tag/get/response",
                    {
                        "tag": tag,
                        "value": state_data["previous_state"]
                    }
                )
        
        # Set up tag set handler
        async def tag_set_handler(data: Dict[str, Any]) -> None:
            """Handle tag set requests."""
            tag = data.get("tag")
            value = data.get("value")
            
            if tag == "system_state.state":
                state_data["previous_state"] = state_data["current_state"]
                state_data["current_state"] = value
            elif tag == "system_state.previous_state":
                state_data["previous_state"] = value
        
        await broker.subscribe("tag/get", tag_get_handler)
        await broker.subscribe("tag/set", tag_set_handler)
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
    current_state = await state_manager.get_current_state()
    assert current_state == "INITIALIZING"
    assert state_manager._message_broker is not None
    assert state_manager._config_manager is not None

@pytest.mark.asyncio
async def test_state_manager_valid_transition(state_manager: StateManager) -> None:
    """Test valid state transition."""
    # INITIALIZING -> READY -> RUNNING
    await state_manager.set_state("READY")
    assert await state_manager.get_current_state() == "READY"
    
    await state_manager.set_state("RUNNING")
    assert await state_manager.get_current_state() == "RUNNING"

@pytest.mark.asyncio
async def test_state_manager_invalid_transition(state_manager: StateManager) -> None:
    """Test invalid state transition is rejected."""
    # Can't go from INITIALIZING to RUNNING
    current_state = await state_manager.get_current_state()
    await state_manager.set_state("RUNNING")
    assert await state_manager.get_current_state() == current_state

@pytest.mark.asyncio
async def test_state_manager_error_transition(state_manager: StateManager) -> None:
    """Test transition to error state."""
    # Any state can transition to ERROR
    await state_manager.set_state("ERROR")
    assert await state_manager.get_current_state() == "ERROR"
    
    # ERROR can only transition to INITIALIZING
    await state_manager.set_state("INITIALIZING")
    assert await state_manager.get_current_state() == "INITIALIZING"

@pytest.mark.asyncio
async def test_state_manager_state_change_event(
    state_manager: StateManager,
    message_broker: MessageBroker
) -> None:
    """Test state change events are published."""
    callback = AsyncMock()
    await message_broker.subscribe("state/change", callback)
    
    await state_manager.set_state("READY")
    await asyncio.sleep(0.1)  # Allow time for event processing
    
    callback.assert_called_once()
    event_data = callback.call_args[0][0]
    assert event_data["previous_state"] == "INITIALIZING"
    assert event_data["current_state"] == "READY"
    assert "timestamp" in event_data

@pytest.mark.asyncio
async def test_state_manager_tag_updates(
    state_manager: StateManager,
    message_broker: MessageBroker
) -> None:
    """Test state changes update tags."""
    tag_updates = []
    
    async def collect_tag_updates(data: Dict[str, Any]) -> None:
        tag_updates.append(data)
    
    await message_broker.subscribe("tag/set", collect_tag_updates)
    
    await state_manager.set_state("READY")
    await asyncio.sleep(0.1)  # Allow time for tag updates
    
    assert any(
        update["tag"] == "system_state.state" and update["value"] == "READY"
        for update in tag_updates
    )
    assert any(
        update["tag"] == "system_state.previous_state" and update["value"] == "INITIALIZING"
        for update in tag_updates
    )

@pytest.mark.asyncio
async def test_state_manager_config_update(
    state_manager: StateManager,
    message_broker: MessageBroker
) -> None:
    """Test state manager handles config updates."""
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
    await asyncio.sleep(0.1)  # Allow time for config update
    
    # Should be able to transition to new state
    await state_manager.set_state("TEST_STATE")
    assert await state_manager.get_current_state() == "TEST_STATE"

@pytest.mark.asyncio
async def test_state_manager_error_handling(
    state_manager: StateManager,
    message_broker: MessageBroker
) -> None:
    """Test error handling during state operations."""
    error_handler = AsyncMock()
    await message_broker.subscribe("error", error_handler)
    
    # Force an error by setting an invalid state
    await state_manager.set_state("INVALID_STATE")
    await asyncio.sleep(0.1)  # Allow time for error handling
    
    error_handler.assert_called_once()
    error_data = error_handler.call_args[0][0]
    assert "error" in error_data
    assert "state" in error_data["topic"]