"""Tag Manager test suite.

Tests hardware interface according to architecture rules:
- TagManager is only component using hardware clients
- All components use MessageBroker for tag access
- Must handle connection loss gracefully
- Must follow tag operation message patterns

Run with:
    pytest tests/test_tag_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order

from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager

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

@order(TestOrder.INFRASTRUCTURE)
class TestTagManager:
    """Tag Manager tests run with infrastructure."""
    
    @pytest.mark.asyncio
    async def test_tag_manager_initialization(self, tag_manager):
        """Test TagManager initialization."""
        assert tag_manager._is_initialized
        assert tag_manager._plc_client is not None

    @pytest.mark.asyncio
    async def test_tag_manager_connection_test(self, tag_manager, mock_plc_client, mock_ssh_client):
        """Test connection testing."""
        # Setup mocks
        mock_plc_client.get_all_tags.return_value = {"test": 1.0}
        mock_ssh_client.write_command.return_value = None
        mock_ssh_client.read_response.return_value = "OK"

        # Test connections
        status = await tag_manager.test_connections()
        assert status["plc"] is True
        assert status["motion_controller"] is True

    @pytest.mark.asyncio
    async def test_tag_manager_connection_failure(self, tag_manager, mock_plc_client):
        """Test connection failure handling."""
        # Simulate connection failure
        mock_plc_client.get_all_tags.side_effect = Exception("Connection failed")

        # Test connections
        status = await tag_manager.test_connections()
        assert status["plc"] is False

        # Verify error published
        errors = []
        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)
        await tag_manager._message_broker.subscribe("error", collect_errors)

        await tag_manager.initialize()
        await asyncio.sleep(0.1)

        assert len(errors) > 0
        assert "Connection failed" in str(errors[0]["error"])

    @pytest.mark.asyncio
    async def test_tag_manager_polling(self, tag_manager, mock_plc_client):
        """Test tag polling and updates."""
        # Set up tag mapping
        tag_manager._plc_tag_map = {
            "motion.x.position": "AMC.Ax1Position",
            "motion.y.position": "AMC.Ax2Position"
        }

        updates = []
        async def collect_updates(data: Dict[str, Any]) -> None:
            updates.append(data)
        await tag_manager._message_broker.subscribe("tag/update", collect_updates)

        # Simulate tag changes
        mock_plc_client.get_all_tags.return_value = {
            "AMC.Ax1Position": 100.0,
            "AMC.Ax2Position": 200.0
        }

        await tag_manager.initialize()
        await asyncio.sleep(0.2)  # Give time for polling

        assert len(updates) > 0
        assert "motion.x.position" in updates[0]["tag"]

    @pytest.mark.asyncio
    async def test_tag_manager_polling_error(self, tag_manager, mock_plc_client):
        """Test polling error handling."""
        errors = []
        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)
        await tag_manager._message_broker.subscribe("error", collect_errors)

        # Set up tag mapping
        tag_manager._plc_tag_map = {
            "motion.x.position": "AMC.Ax1Position"
        }

        # Simulate polling failure
        mock_plc_client.get_all_tags.side_effect = Exception("Poll failed")

        await tag_manager.initialize()
        await asyncio.sleep(0.2)  # Give time for polling error

        assert len(errors) > 0
        assert "Poll failed" in str(errors[0]["error"])

    @pytest.mark.asyncio
    async def test_tag_manager_set_tag(self, tag_manager, mock_plc_client):
        """Test tag setting."""
        # Test setting PLC tag
        await tag_manager._message_broker.publish(
            "tag/set",
            {
                "tag": "motion.position.x_position",
                "value": 100.0
            }
        )
        await asyncio.sleep(0.1)

        mock_plc_client.write_tag.assert_called_once()

    @pytest.mark.asyncio
    async def test_tag_manager_get_tag(self, tag_manager, mock_plc_client):
        """Test tag getting."""
        responses = []
        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)
        await tag_manager._message_broker.subscribe("tag/get/response", collect_responses)

        # Request tag value
        await tag_manager._message_broker.publish(
            "tag/get",
            {
                "tag": "motion.position.x_position"
            }
        )
        await asyncio.sleep(0.1)

        assert len(responses) > 0
        assert "value" in responses[0]
        assert "timestamp" in responses[0]