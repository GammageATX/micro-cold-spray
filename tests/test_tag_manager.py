# tests/test_tag_manager.py

import pytest
import yaml
from unittest.mock import MagicMock, AsyncMock
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager

@pytest.fixture
def message_broker():
    broker = MessageBroker()
    broker._subscribers = {}  # Reset subscribers for clean test environment
    return broker

@pytest.fixture
def config_manager(message_broker):
    # Load the actual configuration files
    with open('config/tags.yaml', 'r') as f:
        tags_config = yaml.safe_load(f)
    with open('config/hardware.yaml', 'r') as f:
        hardware_config = yaml.safe_load(f)
    
    config_manager = ConfigManager(message_broker)
    config_manager._configs = {
        'tags': tags_config,
        'hardware': hardware_config
    }
    return config_manager

@pytest.fixture
def tag_manager(message_broker, config_manager):
    return TagManager(config_manager, message_broker)

def test_tag_manager_initialization(tag_manager):
    assert tag_manager is not None
    assert isinstance(tag_manager, TagManager)

@pytest.mark.asyncio
async def test_tag_manager_set_get_tag(tag_manager):
    await tag_manager.set_tag('motion.position.x_position', 123.45)
    value = tag_manager.get_tag('motion.position.x_position')
    assert value == 123.45

@pytest.mark.asyncio
async def test_tag_manager_handle_tag_set(tag_manager, message_broker):
    await tag_manager._handle_tag_set({'tag': 'motion.position.x_position', 'value': 456.78})
    value = tag_manager.get_tag('motion.position.x_position')
    assert value == 456.78

@pytest.mark.asyncio
async def test_tag_manager_handle_tag_get(tag_manager, message_broker):
    await tag_manager.set_tag('motion.position.x_position', 789.01)
    await tag_manager._handle_tag_get({'tag': 'motion.position.x_position'})
    # Assuming the message broker publishes the response
    response = await message_broker.request('tag_get_response', {'tag': 'motion.position.x_position'})
    assert response['value'] == 789.01

@pytest.mark.asyncio
async def test_tag_manager_poll_hardware_tags(tag_manager):
    tag_manager._plc_client = AsyncMock()
    tag_manager._plc_client.is_connected = True
    tag_manager._plc_client.read_tag = AsyncMock(return_value=100.0)
    await tag_manager._poll_hardware_tags()
    value = tag_manager.get_tag('motion.position.x_position')
    assert value == 100.0

@pytest.mark.asyncio
async def test_tag_manager_publish_connection_states(tag_manager, message_broker):
    await tag_manager._publish_connection_states()
    response = await message_broker.request('hardware_status', {})
    assert response['plc_connected'] == tag_manager.is_plc_connected()
    assert response['ssh_connected'] == tag_manager.is_ssh_connected()