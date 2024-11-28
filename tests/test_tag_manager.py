# tests/test_tag_manager.py

"""Tag Manager test suite.

Run with:
    pytest tests/test_tag_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from collections import defaultdict

from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a clean MessageBroker instance."""
    broker = MessageBroker()
    broker._subscribers = defaultdict(set, {
        # Tag topics
        "tag/set": set(),
        "tag/get": set(),
        "tag/update": set(),
        
        # Hardware topics
        "hardware/connection": set(),
        "hardware/error": set(),
        
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
    
    # Add tag config
    config._configs['tags'] = {
        'tag_groups': {
            'motion': {
                'x_position': {
                    'description': "X axis position",
                    'type': "float",
                    'unit': "mm",
                    'access': "read",
                    'mapped': True,
                    'plc_tag': "XAxis.Position"
                }
            }
        }
    }
    
    # Add hardware config with proper sections
    config._configs['hardware'] = {
        'plc': {
            'tag_file': 'tests/data/test_tags.csv',
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
    
    try:
        yield config
    finally:
        await config.shutdown()

@pytest.fixture
def mock_plc_client() -> MagicMock:
    """Provide a mock PLC client."""
    client = MagicMock()
    client.get_all_tags = AsyncMock(return_value={
        "XAxis.Position": 100.0,
        "YAxis.Position": 200.0,
        "MainFlow.Value": 50.0
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
    """Provide a TagManager instance with mock clients."""
    manager = TagManager(message_broker, config_manager)
    
    # Set mocks before initialization
    manager._plc_client = mock_plc_client
    manager._ssh_client = mock_ssh_client
    
    try:
        await manager.initialize()
        yield manager
    finally:
        if hasattr(manager, '_polling_task') and manager._polling_task:
            manager._polling_task.cancel()
            try:
                await manager._polling_task
            except asyncio.CancelledError:
                pass
        await manager.shutdown()

@pytest.mark.asyncio
async def test_tag_manager_initialization(tag_manager: TagManager) -> None:
    """Test TagManager initializes correctly."""
    assert tag_manager._message_broker is not None
    assert tag_manager._config_manager is not None
    assert tag_manager._plc_client is not None
    assert tag_manager._ssh_client is not None
    assert tag_manager._is_initialized

@pytest.mark.asyncio
async def test_tag_manager_plc_read(
    tag_manager: TagManager,
    mock_plc_client: MagicMock
) -> None:
    """Test PLC tag reading."""
    # Reset mock call count
    mock_plc_client.get_all_tags.reset_mock()
    
    # Set up mock return value
    mock_plc_client.get_all_tags.return_value = {
        "XAxis.Position": 100.0,
        "YAxis.Position": 200.0
    }
    
    # Request tag value
    response = await tag_manager._message_broker.request(
        "tag/get",
        {"tag": "motion.x_position"}
    )
    
    assert response["value"] == 100.0
    assert mock_plc_client.get_all_tags.call_count == 1

@pytest.mark.asyncio
async def test_tag_manager_plc_write(
    tag_manager: TagManager,
    mock_plc_client: MagicMock
) -> None:
    """Test PLC tag writing."""
    # Add tag to config
    tag_manager._tag_config['tag_groups']['process'] = {
        'main_flow': {
            'description': "Main flow rate",
            'type': "float",
            'unit': "slpm",
            'access': "read/write",
            'mapped': True,
            'plc_tag': "MainFlow.Value"
        }
    }
    tag_manager._build_tag_maps()  # Rebuild maps with new tag
    
    # Set tag value
    await tag_manager._message_broker.publish(
        "tag/set",
        {
            "tag": "process.main_flow",
            "value": 75.0
        }
    )
    await asyncio.sleep(0.1)  # Allow time for processing
    
    mock_plc_client.write_tag.assert_called_once_with("MainFlow.Value", 75.0)

@pytest.mark.asyncio
async def test_tag_manager_updates(
    tag_manager: TagManager,
    message_broker: MessageBroker
) -> None:
    """Test tag update publishing."""
    updates = []
    async def collect_updates(data: Dict[str, Any]) -> None:
        updates.append(data)
    await message_broker.subscribe("tag/update", collect_updates)
    
    # Simulate PLC update
    tag_manager._tag_values["motion.x_position"] = 150.0
    await tag_manager._message_broker.publish(
        "tag/update",
        {
            "motion.x_position": 150.0,
            "timestamp": datetime.now().isoformat()
        }
    )
    await asyncio.sleep(0.1)  # Allow time for processing
    
    assert len(updates) > 0
    assert "motion.x_position" in updates[0]
    assert updates[0]["motion.x_position"] == 150.0

@pytest.mark.asyncio
async def test_tag_manager_error_handling(
    tag_manager: TagManager,
    mock_plc_client: MagicMock,
    message_broker: MessageBroker
) -> None:
    """Test error handling during tag operations."""
    # Track errors
    errors = []
    async def collect_errors(data: Dict[str, Any]) -> None:
        errors.append(data)
    await message_broker.subscribe("error", collect_errors)
    
    # Simulate PLC error
    mock_plc_client.get_all_tags.side_effect = Exception("PLC communication error")
    
    # Try to get tag value
    await tag_manager._handle_tag_get({"tag": "motion.x_position"})
    await asyncio.sleep(0.1)  # Allow time for error handling
    
    assert len(errors) > 0
    error = errors[0]
    assert "error" in error
    assert "PLC communication error" in error["error"]

@pytest.mark.asyncio
async def test_tag_manager_connection_status(
    tag_manager: TagManager,
    mock_plc_client: MagicMock,
    message_broker: MessageBroker
) -> None:
    """Test connection status updates."""
    # Track connection status
    status_updates = []
    async def collect_status(data: Dict[str, Any]) -> None:
        status_updates.append(data)
    await message_broker.subscribe("hardware/connection", collect_status)
    
    # Test successful connection
    mock_plc_client.get_all_tags.return_value = {"XAxis.Position": 0.0}
    await tag_manager._poll_tags()  # Force a poll cycle
    await asyncio.sleep(0.1)
    
    # Verify connected status
    assert len(status_updates) > 0
    assert status_updates[-1]["device"] == "plc"
    assert status_updates[-1]["connected"] is True
    
    # Test failed connection
    mock_plc_client.get_all_tags.side_effect = Exception("Connection lost")
    await tag_manager._poll_tags()  # Force a poll cycle
    await asyncio.sleep(0.1)
    
    # Verify disconnected status
    assert any(
        update["device"] == "plc" and 
        update["connected"] is False and
        "error" in update
        for update in status_updates
    )

@pytest.mark.asyncio
async def test_tag_manager_connection_test(
    tag_manager: TagManager,
    mock_plc_client: MagicMock,
    mock_ssh_client: MagicMock
) -> None:
    """Test connection testing functionality."""
    # Test successful connections
    mock_plc_client.get_all_tags.return_value = {"test": 0}
    mock_ssh_client.write_command.return_value = None
    mock_ssh_client.read_response.return_value = "test"
    
    status = await tag_manager.test_connections()
    assert status["plc"] is True
    assert status["motion_controller"] is True
    
    # Test failed PLC connection
    mock_plc_client.get_all_tags.side_effect = Exception("Connection failed")
    status = await tag_manager.test_connections()
    assert status["plc"] is False
    assert status["motion_controller"] is True
    
    # Test failed SSH connection
    mock_ssh_client.write_command.side_effect = Exception("SSH error")
    status = await tag_manager.test_connections()
    assert status["plc"] is False
    assert status["motion_controller"] is False