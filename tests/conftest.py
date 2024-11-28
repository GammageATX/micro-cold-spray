"""Test fixtures and configuration.

Test Order Dependencies:
1. Infrastructure (MessageBroker, ConfigManager, TagManager, StateManager)
2. Process Components (Validator, Parameters, Patterns, Actions, Sequences)
3. UI Components (UIUpdateManager, Widgets)

Run with:
    pytest tests/ -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
import yaml
from loguru import logger
from collections import defaultdict

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager

# Define test order dependencies
pytest.mark.tryfirst
class TestOrder:
    """Test execution order markers."""
    INFRASTRUCTURE = pytest.mark.dependency(name="infrastructure")
    PROCESS = pytest.mark.dependency(depends=["infrastructure"])
    UI = pytest.mark.dependency(name="ui", depends=["infrastructure", "process"])

@pytest.fixture(scope="function")
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a MessageBroker instance."""
    broker = MessageBroker()
    broker._subscribers = defaultdict(set)
    broker._subscribers.update({
        # Core topics from .cursorrules
        "tag/update": set(),
        "tag/get": set(), 
        "tag/set": set(),
        "tag/get/response": set(),
        "state/request": set(),
        "state/change": set(),
        "state/error": set(),
        "error": set()
    })
    
    await broker.start()
    yield broker
    await broker.shutdown()

@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[ConfigManager, None]:
    """Provide a read-only ConfigManager instance."""
    config = ConfigManager(message_broker)
    
    # Mock file operations to prevent any disk writes
    config._save_config = AsyncMock()
    config.update_config = AsyncMock()
    config._load_config = AsyncMock()
    config.save_backup = AsyncMock()
    
    # Use in-memory test configs
    config._configs = {
        'application': {'version': '1.0.0'},
        'hardware': {'version': '1.0.0'},
        'messaging': {'version': '1.0.0'},
        'operation': {'version': '1.0.0'},
        'process': {'version': '1.0.0'},
        'state': {'version': '1.0.0'},
        'tags': {'version': '1.0.0'}
    }
    
    try:
        yield config
    finally:
        # Clean shutdown without saving
        config.shutdown = AsyncMock()
        await config.shutdown()

@pytest.fixture
def mock_plc_client() -> MagicMock:
    """Provide a mock PLC client."""
    client = MagicMock()
    client.get_all_tags = AsyncMock()
    client.write_tag = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client

@pytest.fixture
def mock_ssh_client() -> MagicMock:
    """Provide a mock SSH client."""
    client = MagicMock()
    client.write_command = AsyncMock()
    client.read_response = AsyncMock(return_value="OK")
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client

@pytest.fixture
async def state_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> AsyncGenerator[StateManager, None]:
    """Provide a StateManager instance."""
    # Mock state config
    config_manager._configs["state"] = {
        "transitions": {
            "INITIALIZING": ["READY"],
            "READY": ["RUNNING", "SHUTDOWN"],
            "RUNNING": ["READY", "ERROR"],
            "ERROR": ["READY", "SHUTDOWN"],
            "SHUTDOWN": []
        }
    }
    
    manager = StateManager(
        message_broker=message_broker,
        config_manager=config_manager
    )
    
    try:
        # Initialize subscriptions but don't send hardware signals
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@pytest.fixture(scope="function")
async def tag_manager(message_broker: MessageBroker, config_manager: ConfigManager) -> AsyncGenerator[TagManager, None]:
    """Provide a TagManager instance."""
    from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
    from unittest.mock import patch
    
    # Simple tag configuration for testing
    config_manager._configs["tags"] = {
        "motion": {
            "x": {
                "position": {"type": "float"},
                "velocity": {"type": "float"},
                "status": {"type": "int"}
            }
        },
        "chamber": {
            "pressure": {"type": "float"}
        },
        "flow": {
            "main": {"type": "float"},
            "feeder": {"type": "float"}
        }
    }
    
    # Create mock clients
    mock_plc = AsyncMock()
    mock_plc.get_all_tags = AsyncMock(return_value={
        "motion.x.position": 100.0,
        "motion.x.velocity": 50.0,
        "motion.x.status": 1,
        "chamber.pressure": 2.5,
        "flow.main": 10.0,
        "flow.feeder": 5.0
    })
    
    mock_ssh = AsyncMock()
    mock_ssh.read_response = AsyncMock(return_value="OK")
    
    # Create TagManager with mocked dependencies
    manager = TagManager(
        message_broker=message_broker,
        config_manager=config_manager
    )
    
    # Patch the client creation
    with patch('micro_cold_spray.core.infrastructure.tags.tag_manager.PLCClient', return_value=mock_plc), \
         patch('micro_cold_spray.core.infrastructure.tags.tag_manager.SSHClient', return_value=mock_ssh):
        
        await manager.initialize()
        yield manager
        # No cleanup needed since TagManager handles it in __del__
  