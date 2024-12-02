"""Tag Manager test suite.

Tests tag management functionality:
- Tag reading and writing
- Hardware communication
- Error handling
- Update propagation

Run with:
    pytest tests/test_tag_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from tests.conftest import TestOrder, order

from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.exceptions import HardwareError


@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a MessageBroker instance."""
    broker = MessageBroker()
    await broker.start()
    yield broker
    await broker.shutdown()


@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[ConfigManager, None]:
    """Provide a ConfigManager instance."""
    config = ConfigManager(message_broker)
    config._configs = {
        'tags': {
            'groups': {
                'plc': {
                    'test_tag': {
                        'address': 'DB1.DBX0.0',
                        'type': 'bool',
                        'description': 'Test PLC tag'
                    }
                },
                'motion': {
                    'test_pos': {
                        'address': '/axis1/position',
                        'type': 'float',
                        'description': 'Test motion position',
                        'command': 'get_pos({value})'
                    }
                }
            }
        },
        'hardware': {
            'plc': {
                'ip': '192.168.1.1',
                'rack': 0,
                'slot': 1
            },
            'motion': {
                'host': 'localhost',
                'port': 22,
                'username': 'root',
                'password': 'password'
            }
        },
        'application': {
            'development': {
                'mock_hardware': True
            }
        }
    }

    config.update_config = AsyncMock()
    config._load_config = AsyncMock()
    config._save_config = AsyncMock()

    await config.initialize()
    yield config
    await config.shutdown()


@pytest.fixture
def mock_plc_client() -> MagicMock:
    """Provide a mock PLC client."""
    client = MagicMock()
    client.read_tag = AsyncMock(return_value=True)
    client.write_tag = AsyncMock(return_value=True)
    client.get_all_tags = AsyncMock(return_value={'DB1.DBX0.0': True})
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.is_connected = True
    return client


@pytest.fixture
def mock_ssh_client() -> MagicMock:
    """Provide a mock SSH client."""
    client = MagicMock()
    client.write_command = AsyncMock(return_value=("0.0", "", 0))
    client.test_connection = AsyncMock(return_value=True)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.is_connected = True
    return client


@pytest.fixture(autouse=True)
async def cleanup_tasks():
    """Cleanup any pending tasks after each test."""
    yield
    tasks = [t for t in asyncio.all_tasks()
             if t is not asyncio.current_task()]
    for task in tasks:
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass


@pytest.fixture
async def tag_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    mock_plc_client: MagicMock,
    mock_ssh_client: MagicMock
) -> AsyncGenerator[TagManager, None]:
    """Create tag manager with mocked dependencies."""
    manager = TagManager(
        message_broker=message_broker,
        config_manager=config_manager,
        test_mode=True
    )

    # Inject mock clients
    manager._plc_client = mock_plc_client
    manager._ssh_client = mock_ssh_client

    await manager.initialize()
    yield manager

    # Cleanup
    if manager._polling_task and not manager._polling_task.done():
        manager._polling_task.cancel()
        try:
            await manager._polling_task
        except asyncio.CancelledError:
            pass

    await manager.shutdown()


@order(TestOrder.INFRASTRUCTURE)
class TestTagManager:
    """Tag Manager tests run with infrastructure."""

    @pytest.mark.asyncio
    async def test_tag_writing(self, tag_manager):
        """Test tag writing functionality."""
        # Test PLC tag write
        await tag_manager.write_tag("plc.test_tag", True)
        tag_manager._plc_client.write_tag.assert_called_once_with(
            "DB1.DBX0.0", True)

        # Test motion tag write
        await tag_manager.write_tag("motion.test_pos", 10.0)
        tag_manager._ssh_client.write_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_error_handling(self, tag_manager):
        """Test write error handling."""
        # Setup error collection
        errors = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        await tag_manager._message_broker.subscribe("error", collect_errors)
        # Wait for subscription to be ready
        await asyncio.sleep(0.1)

        # Simulate write error
        tag_manager._plc_client.write_tag.side_effect = Exception("Write failed")

        # Should raise HardwareError but still publish error
        with pytest.raises(HardwareError) as exc_info:
            await tag_manager.write_tag("plc.test_tag", True)

        # Wait for message processing
        await asyncio.sleep(0.1)
        await tag_manager._message_broker._message_queue.join()

        assert "Write failed" in str(exc_info.value)
        assert len(errors) == 1
        assert "Write failed" in str(errors[0]["error"])

    @pytest.mark.asyncio
    async def test_tag_updates(self, tag_manager):
        """Test tag update propagation."""
        updates = []

        async def collect_updates(data: Dict[str, Any]) -> None:
            updates.append(data)

        await tag_manager._message_broker.subscribe("tag/update", collect_updates)

        # Trigger tag update
        await tag_manager.write_tag("plc.test_tag", True)
        await asyncio.sleep(0.1)

        assert len(updates) == 1
        assert updates[0]["tag"] == "plc.test_tag"
        assert updates[0]["value"] is True

    @pytest.mark.asyncio
    async def test_polling_errors(self, tag_manager):
        """Test polling error handling."""
        errors = []
        updates = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        async def collect_updates(data: Dict[str, Any]) -> None:
            updates.append(data)

        await tag_manager._message_broker.subscribe("error", collect_errors)
        await tag_manager._message_broker.subscribe("tag/update", collect_updates)

        # Wait for subscriptions to be ready
        await asyncio.sleep(0.1)

        # Set up mock errors
        tag_manager._plc_client.get_all_tags.side_effect = Exception("Read failed")
        tag_manager._ssh_client.test_connection = AsyncMock(
            side_effect=Exception("SSH connection failed")
        )

        # Let the polling loop run once
        try:
            await tag_manager._poll_loop()
        except Exception:
            pass  # Expected exception from polling errors

        # Wait for message processing
        await tag_manager._message_broker._message_queue.join()

        # Check for hardware status update
        plc_status = next(
            (u for u in updates if u.get("tag") == "hardware.plc.connected"), None
        )
        assert plc_status is not None
        assert plc_status["value"] is False

        # Check for SSH status update
        ssh_status = next(
            (u for u in updates if u.get("tag") == "hardware.ssh.connected"), None
        )
        assert ssh_status is not None
        assert ssh_status["value"] is False

        # Verify error messages were published
        assert any("Read failed" in str(error.get("error")) for error in errors)
        assert any("SSH connection failed" in str(error.get("error")) for error in errors)

    @pytest.mark.asyncio
    async def test_tag_getting(self, tag_manager):
        """Test tag getting."""
        responses = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        await tag_manager._message_broker.subscribe("tag/get/response", collect_responses)

        # Request tag value
        await tag_manager._message_broker.publish(
            "tag/get",
            {"tag": "plc.test_tag"}
        )
        await asyncio.sleep(0.1)

        assert len(responses) == 1
        assert responses[0]["tag"] == "plc.test_tag"
        assert "value" in responses[0]
