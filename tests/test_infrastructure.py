# tests/test_infrastructure.py

import pytest
import asyncio
from unittest.mock import MagicMock
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker

@pytest.fixture
def message_broker():
    broker = MessageBroker()
    broker._subscribers = {}  # Reset subscribers for clean test environment
    return broker

@pytest.fixture
def config_manager(message_broker):
    return ConfigManager(message_broker)

@pytest.fixture
def tag_manager():
    return TagManager()

def test_message_broker_initialization(message_broker):
    assert message_broker is not None
    assert isinstance(message_broker, MessageBroker)

def test_config_manager_initialization(config_manager):
    assert config_manager is not None
    assert isinstance(config_manager, ConfigManager)

def test_tag_manager_initialization(tag_manager):
    assert tag_manager is not None
    assert isinstance(tag_manager, TagManager)

def test_message_broker_subscription(message_broker):
    callback = MagicMock()
    message_broker.subscribe('test/topic', callback)
    assert 'test/topic' in message_broker._subscribers
    assert callback in message_broker._subscribers['test/topic']

@pytest.mark.asyncio
async def test_message_broker_publish(message_broker):
    callback = MagicMock()
    message_broker.subscribe('test/topic', callback)
    await message_broker.publish('test/topic', {'key': 'value'})
    callback.assert_called_once_with({'key': 'value'})

def test_config_manager_updates_message_broker(config_manager, message_broker):
    callback = MagicMock()
    message_broker.subscribe('config/update/messaging', callback)
    asyncio.run(config_manager._message_broker.publish('config/update/messaging', {'message_types': {'new_type': 'test'}}))
    callback.assert_called_once_with({'message_types': {'new_type': 'test'}})