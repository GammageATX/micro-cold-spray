"""Tag Manager test suite.

Tests tag management functionality:
- Tag reading and writing
- Hardware communication
- Error handling
- Update propagation

Run with:
    pytest tests/infrastructure/test_tag_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from tests.conftest import TestOrder, order
from pathlib import Path

from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.exceptions import HardwareError


@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a MessageBroker instance."""
    broker = MessageBroker()
    await broker.start()

    # Set all valid topics needed for tests
    valid_topics = {
        'config/request',
        'config/response',
        'config/update',
        'tag/request',
        'tag/response',
        'tag/update',
        'error',
        'hardware/state',
    }
    await broker.set_valid_topics(valid_topics)

    yield broker
    await broker.shutdown()


@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[ConfigManager, None]:
    """Provide a ConfigManager instance."""
    config = ConfigManager(Path("config"), message_broker)
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
        await tag_manager.write_tag("gas_control.feeder_flow.setpoint", 5.0)

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
            await tag_manager.write_tag("gas_control.feeder_flow.setpoint", 5.0)

        # Wait for message processing
        await asyncio.sleep(0.1)
        await tag_manager._message_broker._message_queue.join()

        assert "Write failed" in str(exc_info.value)
        assert len(errors) == 1
        assert errors[0]["source"] == "tag_manager"
        assert "Write failed" in errors[0]["error"]

    @pytest.mark.asyncio
    async def test_tag_updates(self, tag_manager):
        """Test tag update propagation."""
        updates = []

        async def collect_updates(data: Dict[str, Any]) -> None:
            updates.append(data)

        await tag_manager._message_broker.subscribe("tag/update", collect_updates)

        # Trigger tag update
        await tag_manager.write_tag("gas_control.feeder_flow.setpoint", 5.0)

        # Wait for message processing
        await asyncio.sleep(0.1)
        await tag_manager._message_broker._message_queue.join()

        assert len(updates) == 1
        assert updates[0]["tag"] == "gas_control.feeder_flow.setpoint"
        assert updates[0]["value"] == 5.0

    @pytest.mark.asyncio
    async def test_tag_getting(self, tag_manager):
        """Test tag getting."""
        responses = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        await tag_manager._message_broker.subscribe("tag/response", collect_responses)

        # Request tag value using request/response pattern
        await tag_manager._message_broker.publish(
            "tag/request",
            {
                "request_type": "get",
                "tag": "gas_control.feeder_flow.measured",
                "request_id": "test-123"
            }
        )
        await asyncio.sleep(0.1)

        assert len(responses) == 1
        assert responses[0]["tag"] == "gas_control.feeder_flow.measured"
        assert responses[0]["request_id"] == "test-123"
        assert "value" in responses[0]

    @pytest.mark.asyncio
    async def test_tag_request_get(self, tag_manager):
        """Test tag get request/response pattern."""
        responses = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        await tag_manager._message_broker.subscribe("tag/response", collect_responses)

        # Send get request
        await tag_manager._message_broker.publish(
            "tag/request",
            {
                "request_type": "get",
                "tag": "gas_control.feeder_flow.measured",
                "request_id": "test-123"
            }
        )
        await asyncio.sleep(0.1)

        # Verify response
        assert len(responses) == 1
        assert responses[0]["request_id"] == "test-123"
        assert responses[0]["tag"] == "gas_control.feeder_flow.measured"
        assert "value" in responses[0]

    @pytest.mark.asyncio
    async def test_tag_request_set(self, tag_manager):
        """Test tag set request/response pattern."""
        responses = []
        updates = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        async def collect_updates(data: Dict[str, Any]) -> None:
            updates.append(data)

        await tag_manager._message_broker.subscribe("tag/response", collect_responses)
        await tag_manager._message_broker.subscribe("tag/update", collect_updates)

        # Send set request
        await tag_manager._message_broker.publish(
            "tag/request",
            {
                "request_type": "set",
                "tag": "gas_control.feeder_flow.setpoint",
                "value": 5.0,
                "request_id": "test-456"
            }
        )
        await asyncio.sleep(0.1)

        # Verify response
        assert len(responses) == 1
        assert responses[0]["request_id"] == "test-456"
        assert responses[0]["tag"] == "gas_control.feeder_flow.setpoint"
        assert responses[0]["value"] == 5.0

        # Verify update
        assert len(updates) == 1
        assert updates[0]["tag"] == "gas_control.feeder_flow.setpoint"
        assert updates[0]["value"] == 5.0

    @pytest.mark.asyncio
    async def test_tag_request_errors(self, tag_manager):
        """Test tag request error handling."""
        errors = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        await tag_manager._message_broker.subscribe("error", collect_errors)

        # Test missing request type
        await tag_manager._message_broker.publish(
            "tag/request",
            {
                "tag": "plc.test_tag",
                "request_id": "test-789"
            }
        )
        await asyncio.sleep(0.1)

        assert len(errors) == 1
        assert "Missing request_type" in errors[0]["error"]
        assert errors[0]["request_id"] == "test-789"

        # Test invalid request type
        await tag_manager._message_broker.publish(
            "tag/request",
            {
                "request_type": "invalid",
                "tag": "plc.test_tag",
                "request_id": "test-abc"
            }
        )
        await asyncio.sleep(0.1)

        assert len(errors) == 2
        assert "Invalid request_type" in errors[1]["error"]
        assert errors[1]["request_id"] == "test-abc"

        # Test missing value in set request
        await tag_manager._message_broker.publish(
            "tag/request",
            {
                "request_type": "set",
                "tag": "plc.test_tag",
                "request_id": "test-def"
            }
        )
        await asyncio.sleep(0.1)

        assert len(errors) == 3
        assert "Missing value" in errors[2]["error"]
        assert errors[2]["request_id"] == "test-def"

    @pytest.mark.asyncio
    async def test_hardware_state_lifecycle(self, tag_manager):
        """Test hardware state updates through component lifecycle."""
        # Force mock mode off so clients initialize
        tag_manager._mock_mode = False

        states = []

        async def collect_states(data: Dict[str, Any]) -> None:
            states.append(data)

        await tag_manager._message_broker.subscribe("hardware/state", collect_states)

        # Initialize
        await tag_manager.initialize()
        await asyncio.sleep(0.1)

        # Should see initial connected states
        init_states = [s for s in states if s["state"] == "connected"]
        assert len(init_states) == 2  # Both PLC and motion

        # Simulate error
        await tag_manager._publish_hardware_state("plc", "error", "Connection lost")
        await asyncio.sleep(0.1)

        error_state = next(s for s in states if s["state"] == "error")
        assert error_state["device"] == "plc"
        assert error_state["error"] == "Connection lost"

        # Shutdown
        await tag_manager.shutdown()
        await asyncio.sleep(0.1)

        # Should see disconnected states
        final_states = [s for s in states if s["state"] == "disconnected"]
        assert len(final_states) == 2  # Both clients disconnect
