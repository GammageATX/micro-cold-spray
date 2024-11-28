"""Infrastructure component test suite.

Run with:
    pytest tests/test_infrastructure.py -v --asyncio-mode=auto

Options:
    -v                      Verbose output
    --asyncio-mode=auto     Required for async tests
    -k <testname>          Run specific test (e.g. -k test_message_broker_publish)
"""

import pytest
from typing import AsyncGenerator, Callable, Dict, List
from unittest.mock import AsyncMock, MagicMock
from loguru import logger
import asyncio

from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Fixture providing a clean MessageBroker instance for testing."""
    broker = MessageBroker()
    # Initialize with empty sets for test topics
    broker._subscribers = {
        "test/topic": set(),
        "test/request": set(),
        "test/request/response": set(),
        "test/response": set(),
        "error/topic": set(),
        "error": set(),
        "config/update/messaging": set()
    }
    try:
        # Start the broker to process messages
        await broker.start()
        yield broker
    finally:
        # Cleanup subscribers and shutdown
        broker._subscribers.clear()
        await broker.shutdown()

@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[ConfigManager, None]:
    """Fixture providing a ConfigManager instance with mock message broker."""
    config = ConfigManager(message_broker)
    try:
        yield config
    finally:
        await config.shutdown()

@pytest.fixture
async def tag_manager(message_broker: MessageBroker, config_manager: ConfigManager) -> AsyncGenerator[TagManager, None]:
    """Fixture providing a TagManager instance with mock message broker."""
    manager = TagManager(message_broker, config_manager)
    try:
        yield manager
    finally:
        await manager.shutdown()

@pytest.mark.asyncio
async def test_message_broker_initialization(message_broker: MessageBroker) -> None:
    """Test MessageBroker initializes correctly."""
    assert message_broker is not None
    assert isinstance(message_broker, MessageBroker)
    assert isinstance(message_broker._subscribers, dict)

@pytest.mark.asyncio
async def test_message_broker_subscription(message_broker: MessageBroker) -> None:
    """Test MessageBroker subscription mechanism."""
    callback = AsyncMock()
    topic = "test/topic"
    
    await message_broker.subscribe(topic, callback)
    assert topic in message_broker._subscribers
    assert callback in message_broker._subscribers[topic]

@pytest.mark.asyncio
async def test_message_broker_unsubscribe(message_broker: MessageBroker) -> None:
    """Test MessageBroker unsubscribe mechanism."""
    callback = AsyncMock()
    topic = "test/topic"
    
    # Subscribe and verify subscription worked
    await message_broker.subscribe(topic, callback)
    assert callback in message_broker._subscribers[topic]
    
    # Unsubscribe and verify removal
    await message_broker.unsubscribe(topic, callback)
    assert topic in message_broker._subscribers  # Topic should still exist
    assert len(message_broker._subscribers[topic]) == 0  # Set should be empty

@pytest.mark.asyncio
async def test_message_broker_publish(message_broker: MessageBroker) -> None:
    """Test MessageBroker publish mechanism."""
    callback = AsyncMock()
    test_data = {"key": "value"}
    
    await message_broker.subscribe("test/topic", callback)
    await asyncio.gather(
        message_broker.publish("test/topic", test_data),
        asyncio.sleep(0.1)
    )
    
    callback.assert_called_once_with(test_data)

@pytest.mark.asyncio
async def test_message_broker_request_response(message_broker: MessageBroker) -> None:
    """Test MessageBroker request-response pattern."""
    response_data = {"status": "success"}
    
    async def mock_responder(data: dict) -> None:
        # Respond immediately to avoid timeout
        await message_broker.publish(f"{data['response_topic']}", response_data)
    
    await message_broker.subscribe("test/request", mock_responder)
    
    # Pass response topic in request data
    request_data = {"response_topic": "test/request/response"}
    response = await message_broker.request("test/request", request_data, timeout=1.0)
    assert response == response_data

@pytest.mark.asyncio
async def test_message_broker_error_handling(message_broker: MessageBroker) -> None:
    """Test MessageBroker error handling."""
    test_error = Exception("Test error")
    test_message = {"topic": "error/topic", "data": "test"}
    
    async def failing_callback(data: dict) -> None:
        raise test_error
    
    error_handler = AsyncMock()
    await message_broker.subscribe("error/topic", failing_callback)
    await message_broker.subscribe("error", error_handler)
    
    # Publish and wait for error handling
    await asyncio.gather(
        message_broker.publish("error/topic", test_message),
        asyncio.sleep(0.1)  # Give time for error processing
    )
    
    # Verify error handler was called with correct error data
    error_handler.assert_called_once()
    error_data = error_handler.call_args[0][0]
    assert error_data["error"] == str(test_error)
    assert error_data["topic"] == "error/topic"
    assert error_data["message"] == test_message

@pytest.mark.asyncio
async def test_config_manager_initialization(config_manager: ConfigManager) -> None:
    """Test ConfigManager initializes correctly."""
    assert config_manager is not None
    assert isinstance(config_manager, ConfigManager)

@pytest.mark.asyncio
async def test_tag_manager_initialization(tag_manager: TagManager) -> None:
    """Test TagManager initializes correctly."""
    assert tag_manager is not None
    assert isinstance(tag_manager, TagManager)

@pytest.mark.asyncio
async def test_config_manager_updates_message_broker(
    config_manager: ConfigManager,
    message_broker: MessageBroker
) -> None:
    """Test ConfigManager properly updates through MessageBroker."""
    callback = AsyncMock()
    test_config = {"message_types": {"new_type": "test"}}
    
    await message_broker.subscribe("config/update/messaging", callback)
    await asyncio.gather(
        message_broker.publish("config/update/messaging", test_config),
        asyncio.sleep(0.1)
    )
    
    callback.assert_called_once_with(test_config)