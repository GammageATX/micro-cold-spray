"""Infrastructure test suite.

Tests core infrastructure components:
- MessageBroker
- ConfigManager
- TagManager
- StateManager

Run with:
    pytest tests/test_infrastructure.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
import asyncio
from datetime import datetime
from collections import defaultdict
from unittest.mock import MagicMock

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from tests.conftest import TestOrder, order


@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a MessageBroker instance."""
    broker = MessageBroker()
    await broker.start()
    yield broker
    await broker.shutdown()


@pytest.fixture
async def mock_config_manager(message_broker) -> AsyncGenerator[ConfigManager, None]:
    """Create a mock config manager instance."""
    manager = MagicMock(spec=ConfigManager)
    manager._message_broker = message_broker
    manager._configs = {}

    async def mock_update_config(name: str, config: Dict[str, Any]) -> None:
        manager._configs[name] = config
        await message_broker.publish(f"config/update/{name}", config)

    manager.update_config = mock_update_config
    yield manager


@order(TestOrder.INFRASTRUCTURE)
class TestInfrastructure:
    """Infrastructure tests run first."""

    @pytest.mark.asyncio
    async def test_message_broker_startup(self, message_broker):
        """Test MessageBroker initialization."""
        assert message_broker._subscribers == defaultdict(list)
        assert message_broker._running is True

    @pytest.mark.asyncio
    async def test_message_subscription(self, message_broker):
        """Test message subscription and publishing."""
        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await message_broker.subscribe("test/topic", collect_messages)

        # Test single message
        test_data = {
            "value": 42,
            "timestamp": datetime.now().isoformat()
        }
        await message_broker.publish("test/topic", test_data)
        await asyncio.sleep(0.1)  # Allow time for async processing
        assert len(messages) == 1
        assert messages[0]["value"] == 42

        # Test multiple messages
        for i in range(3):
            await message_broker.publish("test/topic", {"count": i})
        await asyncio.sleep(0.1)
        assert len(messages) == 4  # 1 from before + 3 new

        # Test unsubscribe
        await message_broker.unsubscribe("test/topic", collect_messages)
        await message_broker.publish("test/topic", {"final": True})
        await asyncio.sleep(0.1)
        assert len(messages) == 4  # No new messages after unsubscribe

    @pytest.mark.asyncio
    async def test_error_handling(self, message_broker):
        """Test error handling in MessageBroker."""
        errors = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        await message_broker.subscribe("error", collect_errors)

        # Test error in subscriber
        async def bad_subscriber(data: Dict[str, Any]) -> None:
            raise Exception("Test error")

        await message_broker.subscribe("test/error", bad_subscriber)
        await message_broker.publish("test/error", {"trigger": "error"})
        await asyncio.sleep(0.1)

        assert len(errors) == 1
        assert "error" in errors[0]
        assert "Test error" in str(errors[0]["error"])

    @pytest.mark.asyncio
    async def test_config_updates(self, mock_config_manager):
        """Test config updates are published."""
        updates = []

        async def collect_updates(data: Dict[str, Any]) -> None:
            updates.append(data)

        await mock_config_manager._message_broker.subscribe(
            "config/update/test",
            collect_updates
        )

        test_config = {
            "key": "value",
            "timestamp": datetime.now().isoformat()
        }
        await mock_config_manager.update_config("test", test_config)
        await asyncio.sleep(0.1)

        assert len(updates) == 1
        assert updates[0]["key"] == "value"
        assert test_config == mock_config_manager._configs["test"]
