"""Message Broker test suite.

Tests message broker functionality:
- Topic validation
- Pub/sub patterns
- Error handling
- Message delivery

Run with:
    pytest tests/infrastructure/test_message_broker.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.exceptions import MessageError


@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Create MessageBroker instance."""
    broker = MessageBroker(test_mode=True)
    await broker.start()

    # Set valid topics for testing
    valid_topics = {
        "test/request", "test/response",
        "error",
        "config/request", "config/response", "config/update",
        "tag/request", "tag/response", "tag/update",
        "hardware/state",
        "sequence/request", "sequence/response", "sequence/error",
        "sequence/status", "sequence/state", "sequence/step",
        "sequence/loaded", "sequence/complete"
    }
    await broker.set_valid_topics(valid_topics)
    broker._initialized = True

    yield broker
    await broker.shutdown()


@order(TestOrder.INFRASTRUCTURE)
class TestMessageBroker:
    """Test MessageBroker functionality."""

    @pytest.mark.asyncio
    async def test_topic_validation(self, message_broker):
        """Test topic validation against application.yaml structure."""
        # Set valid topics from application.yaml structure
        valid_topics = {
            # Core operations
            "tag/request", "tag/response", "tag/update",
            "config/request", "config/response", "config/update",
            "state/request", "state/response", "state/change",
            "sequence/request", "sequence/response", "sequence/state", "sequence/progress",
            "pattern/request", "pattern/response", "pattern/state",
            "action/request", "action/response", "action/state",
            "parameter/request", "parameter/response", "parameter/state",
            "validation/request", "validation/response",
            "data/request", "data/response", "data/state",
            "ui/request", "ui/response", "ui/state",
            "hardware/state",
            "motion/request", "motion/response", "motion/state",
            # System topics
            "system/status", "system/state",
            # Error topic
            "error"
        }
        await message_broker.set_valid_topics(valid_topics)

        # Test valid topic publishing
        await message_broker.publish("tag/request", {"test": True})
        await message_broker.publish("config/response", {"test": True})
        await message_broker.publish("error", {"test": True})

        # Test invalid topics
        with pytest.raises(MessageError, match="Invalid topic"):
            await message_broker.publish("invalid/topic", {"test": True})

        with pytest.raises(MessageError, match="Invalid topic"):
            await message_broker.publish("tag/invalid", {"test": True})

    @pytest.mark.asyncio
    async def test_test_mode_topics(self, message_broker):
        """Test test mode topic handling."""
        # Test topics should work in test mode without explicit validation
        await message_broker.publish("test/request", {"test": True})
        await message_broker.publish("test/response", {"test": True})

        # But other topics should still be validated
        with pytest.raises(MessageError, match="Invalid topic"):
            await message_broker.publish("invalid/topic", {"test": True})

    @pytest.mark.asyncio
    async def test_pub_sub_pattern(self, message_broker):
        """Test publish/subscribe messaging pattern."""
        # Set minimal topics for test
        valid_topics = {
            "tag/request", "tag/response",
            "config/request", "config/response",
            "error"
        }
        await message_broker.set_valid_topics(valid_topics)

        # Test request/response pattern
        responses = []

        async def handle_response(data: Dict[str, Any]) -> None:
            responses.append(data)

        await message_broker.subscribe("tag/response", handle_response)

        test_request = {
            "request_id": "test-123",
            "timestamp": datetime.now().isoformat()
        }
        await message_broker.publish("tag/request", test_request)
        await message_broker.publish("tag/response", {
            "request_id": "test-123",
            "success": True,
            "timestamp": datetime.now().isoformat()
        })
        await asyncio.sleep(0.1)

        assert len(responses) == 1
        assert responses[0]["request_id"] == "test-123"
        assert responses[0]["success"] is True

    @pytest.mark.asyncio
    async def test_error_handling(self, message_broker):
        """Test error handling and propagation."""
        errors = []

        async def handle_error(data: Dict[str, Any]) -> None:
            errors.append(data)

        await message_broker.subscribe("error", handle_error)

        # Test error publishing
        error_msg = {
            "source": "test",
            "error": "Test error",
            "timestamp": datetime.now().isoformat()
        }
        await message_broker.publish("error", error_msg)
        await asyncio.sleep(0.1)

        assert len(errors) == 1
        assert errors[0]["source"] == "test"
        assert errors[0]["error"] == "Test error"
        assert "timestamp" in errors[0]

        # Test error from invalid topic
        try:
            await message_broker.publish("invalid/topic", {"test": True})
        except MessageError:
            pass
        await asyncio.sleep(0.1)

        assert len(errors) == 2
        assert errors[1]["source"] == "message_broker"
        assert "Invalid topic" in errors[1]["error"]
        assert "timestamp" in errors[1]

    @pytest.mark.asyncio
    async def test_message_metadata(self, message_broker):
        """Test message metadata handling."""
        valid_topics = {"test/metadata"}
        await message_broker.set_valid_topics(valid_topics)

        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await message_broker.subscribe("test/metadata", collect_messages)

        # Test message without timestamp
        await message_broker.publish("test/metadata", {"test": True})
        await asyncio.sleep(0.1)

        assert len(messages) == 1
        assert "timestamp" in messages[0]
        assert messages[0]["test"] is True

        # Test message with existing timestamp
        custom_time = "2024-01-01T00:00:00"
        await message_broker.publish("test/metadata", {
            "test": True,
            "timestamp": custom_time
        })
        await asyncio.sleep(0.1)

        assert len(messages) == 2
        assert messages[1]["timestamp"] == custom_time

    @pytest.mark.asyncio
    async def test_subscription_management(self, message_broker):
        """Test subscription management."""
        valid_topics = {"test/subscription"}
        await message_broker.set_valid_topics(valid_topics)

        messages = []

        async def handle_message(data: Dict[str, Any]) -> None:
            messages.append(data)

        # Test subscribe
        await message_broker.subscribe("test/subscription", handle_message)
        await message_broker.publish("test/subscription", {"test": 1})
        await asyncio.sleep(0.1)
        assert len(messages) == 1

        # Test unsubscribe
        await message_broker.unsubscribe("test/subscription", handle_message)
        await message_broker.publish("test/subscription", {"test": 2})
        await asyncio.sleep(0.1)
        assert len(messages) == 1  # Should not receive second message

        # Test invalid topic subscription
        with pytest.raises(MessageError, match="Failed to subscribe to topic invalid/topic"):
            await message_broker.subscribe("invalid/topic", handle_message)
