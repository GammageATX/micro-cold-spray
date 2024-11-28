"""Tag Manager test suite.

Tests hardware interface according to .cursorrules:
- TagManager is only component using hardware clients
- All components use MessageBroker for tag access
- Must follow tag operation message patterns
- Must handle connection loss gracefully

Tag Operations:
- Must use "tag/set" for setting values
- Must use "tag/get" for requesting values
- Must use "tag/update" for receiving updates
- Must use "tag/get/response" for get responses
- Must use "error" for operation errors

Run with:
    pytest tests/test_tag_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from collections import defaultdict
from tests.conftest import TestOrder

from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a MessageBroker instance."""
    broker = MessageBroker()
    broker._subscribers = {
        # Tag topics from .cursorrules
        "tag/set": set(),
        "tag/get": set(),
        "tag/update": set(),
        "tag/get/response": set(),
        
        # Hardware topics
        "hardware/status/*": set(),
        "hardware/error": set(),
        
        # Error topics
        "error": set()
    }
    
    try:
        await broker.start()
        yield broker
    finally:
        await broker.shutdown()

@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[ConfigManager, None]:
    """Provide a ConfigManager instance."""
    config = ConfigManager(message_broker)
    
    # Use in-memory configs only
    config._configs = {
        'tags': {
            'tag_groups': {
                'motion': {
                    'position': {
                        'x_position': {
                            'description': "X axis position",
                            'type': "float",
                            'unit': "mm",
                            'access': "read",
                            'mapped': True,
                            'plc_tag': "AMC.Ax1Position"
                        }
                    }
                }
            }
        },
        'hardware': {
            'plc': {
                'ip': '127.0.0.1',
                'port': 44818,
                'timeout': 1.0
            },
            'motion_controller': {
                'host': '127.0.0.1',
                'username': 'test',
                'password': 'test',
                'port': 22
            }
        }
    }
    
    # Mock ALL file operations
    config._save_config = AsyncMock()
    config.update_config = AsyncMock()
    config._load_config = AsyncMock()
    config.save_backup = AsyncMock()
    
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
    # Use real tag names from tags.yaml
    client.get_all_tags = AsyncMock(return_value={
        "AMC.Ax1Position": 100.0,
        "AMC.Ax2Position": 200.0,
        "AOS32-0.1.2.1": 50.0
    })
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
async def tag_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    mock_plc_client: MagicMock,
    mock_ssh_client: MagicMock
) -> AsyncGenerator[TagManager, None]:
    """Provide a TagManager instance."""
    manager = TagManager(
        message_broker=message_broker,
        config_manager=config_manager
    )
    
    # Mock the clients after initialization
    manager._plc_client = mock_plc_client
    manager._ssh_client = mock_ssh_client
    
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@TestOrder.INFRASTRUCTURE
class TestTagManager:
    """Tag Manager tests run with infrastructure."""
    
    @pytest.mark.asyncio
    async def test_tag_manager_initialization(self, tag_manager):
        """Test TagManager initialization."""
        assert tag_manager._is_initialized
        assert tag_manager._plc_client is not None

@pytest.mark.asyncio
async def test_tag_manager_plc_read(tag_manager):
    """Test PLC tag reading."""
    # Track tag updates
    updates = []
    async def collect_updates(data: Dict[str, Any]) -> None:
        updates.append(data)
    await tag_manager._message_broker.subscribe("tag/get/response", collect_updates)
    
    # Request tag value using valid tag from tags.yaml
    await tag_manager._message_broker.publish(
        "tag/get",
        {
            "tag": "motion.position.x_position",
            "timestamp": datetime.now().isoformat()
        }
    )
    await asyncio.sleep(0.1)
    
    # Verify response
    assert len(updates) > 0
    assert "value" in updates[0]
    assert "timestamp" in updates[0]
    assert "tag" in updates[0]