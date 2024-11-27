# tests/test_ui_update_manager.py

import pytest
from unittest.mock import MagicMock, AsyncMock
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager

@pytest.fixture
def message_broker():
    broker = MessageBroker()
    broker._subscribers = {}  # Reset subscribers for clean test environment
    return broker

@pytest.fixture
def config_manager(message_broker):
    config_manager = ConfigManager(message_broker)
    return config_manager

@pytest.fixture
def ui_update_manager(message_broker, config_manager):
    return UIUpdateManager(message_broker, config_manager)

def test_ui_update_manager_initialization(ui_update_manager):
    assert ui_update_manager is not None
    assert isinstance(ui_update_manager, UIUpdateManager)

@pytest.mark.asyncio
async def test_ui_update_manager_start(ui_update_manager):
    await ui_update_manager.start()
    assert 'config/update/*' in ui_update_manager._message_broker._subscribers

@pytest.mark.asyncio
async def test_ui_update_manager_handle_config_update(ui_update_manager):
    await ui_update_manager._handle_config_update({'config_type': 'test', 'data': {'key': 'value'}})
    # Assuming the message broker publishes the update
    response = await ui_update_manager._message_broker.request('config/test', {})
    assert response['key'] == 'value'

@pytest.mark.asyncio
async def test_ui_update_manager_register_widget(ui_update_manager):
    await ui_update_manager.register_widget('widget1', ['tag1', 'tag2'])
    assert 'widget1' in ui_update_manager._registered_widgets
    assert 'tag1' in ui_update_manager._tag_subscriptions
    assert 'tag2' in ui_update_manager._tag_subscriptions

@pytest.mark.asyncio
async def test_ui_update_manager_unregister_widget(ui_update_manager):
    await ui_update_manager.register_widget('widget1', ['tag1', 'tag2'])
    await ui_update_manager.unregister_widget('widget1')
    assert 'widget1' not in ui_update_manager._registered_widgets
    assert 'tag1' not in ui_update_manager._tag_subscriptions
    assert 'tag2' not in ui_update_manager._tag_subscriptions

@pytest.mark.asyncio
async def test_ui_update_manager_send_update(ui_update_manager):
    await ui_update_manager.send_update('test/topic', {'key': 'value'})
    # Assuming the message broker publishes the update
    response = await ui_update_manager._message_broker.request('test/topic', {})
    assert response['key'] == 'value'