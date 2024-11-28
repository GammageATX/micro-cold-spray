# tests/test_ui_update_manager.py

"""UI Update Manager test suite.

Run with:
    pytest tests/test_ui_update_manager.py -v --asyncio-mode=auto
"""

import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from loguru import logger

from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a clean MessageBroker instance."""
    broker = MessageBroker()
    broker._subscribers = {
        "config/update/*": set(),
        "ui/update": set(),
        "tag/update": set(),
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
    try:
        yield config
    finally:
        await config.shutdown()

@pytest.fixture
async def ui_update_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> AsyncGenerator[UIUpdateManager, None]:
    """Provide a UIUpdateManager instance."""
    manager = UIUpdateManager(message_broker, config_manager)
    try:
        await manager.start()
        yield manager
    finally:
        await manager.shutdown()

@pytest.mark.asyncio
async def test_ui_update_manager_initialization(ui_update_manager: UIUpdateManager) -> None:
    """Test UIUpdateManager initializes correctly."""
    assert ui_update_manager is not None
    assert isinstance(ui_update_manager, UIUpdateManager)
    assert ui_update_manager._message_broker is not None
    assert ui_update_manager._config_manager is not None

@pytest.mark.asyncio
async def test_ui_update_manager_handle_config_update(
    ui_update_manager: UIUpdateManager,
    message_broker: MessageBroker
) -> None:
    """Test UIUpdateManager handles config updates."""
    test_config = {
        'config_type': 'test',
        'data': {'key': 'value'}
    }
    
    callback = AsyncMock()
    await message_broker.subscribe('ui/update', callback)
    
    await message_broker.publish('config/update/test', test_config)
    await asyncio.sleep(0.1)  # Allow time for processing
    
    callback.assert_called_once()
    update_data = callback.call_args[0][0]
    assert update_data['type'] == 'config'
    assert update_data['data'] == test_config['data']

@pytest.mark.asyncio
async def test_ui_update_manager_register_widget(ui_update_manager: UIUpdateManager) -> None:
    """Test widget registration."""
    widget_id = 'test_widget'
    tags = ['tag1', 'tag2']
    
    await ui_update_manager.register_widget(widget_id, tags)
    
    assert widget_id in ui_update_manager._registered_widgets
    assert all(tag in ui_update_manager._tag_subscriptions for tag in tags)
    assert all(widget_id in ui_update_manager._tag_subscriptions[tag] for tag in tags)

@pytest.mark.asyncio
async def test_ui_update_manager_unregister_widget(ui_update_manager: UIUpdateManager) -> None:
    """Test widget unregistration."""
    widget_id = 'test_widget'
    tags = ['tag1', 'tag2']
    
    # Register first
    await ui_update_manager.register_widget(widget_id, tags)
    
    # Then unregister
    await ui_update_manager.unregister_widget(widget_id)
    
    assert widget_id not in ui_update_manager._registered_widgets
    assert all(widget_id not in ui_update_manager._tag_subscriptions.get(tag, set()) 
              for tag in tags)

@pytest.mark.asyncio
async def test_ui_update_manager_handle_tag_update(
    ui_update_manager: UIUpdateManager,
    message_broker: MessageBroker
) -> None:
    """Test handling of tag updates."""
    widget_id = 'test_widget'
    tag = 'test_tag'
    value = 42.0
    
    # Register widget for tag
    await ui_update_manager.register_widget(widget_id, [tag])
    
    # Mock the widget's update method
    ui_update_manager._registered_widgets[widget_id] = AsyncMock()
    
    # Publish tag update
    await message_broker.publish('tag/update', {'tag': tag, 'value': value})
    await asyncio.sleep(0.1)  # Allow time for processing
    
    # Verify widget was updated
    ui_update_manager._registered_widgets[widget_id].update.assert_called_once_with(
        tag, value
    )

@pytest.mark.asyncio
async def test_ui_update_manager_error_handling(
    ui_update_manager: UIUpdateManager,
    message_broker: MessageBroker
) -> None:
    """Test error handling during updates."""
    error_handler = AsyncMock()
    await message_broker.subscribe('error', error_handler)
    
    # Register a widget that will raise an error
    widget_id = 'error_widget'
    tag = 'error_tag'
    
    class ErrorWidget:
        async def update(self, tag: str, value: Any) -> None:
            raise Exception("Test error")
    
    await ui_update_manager.register_widget(widget_id, [tag])
    ui_update_manager._registered_widgets[widget_id] = ErrorWidget()
    
    # Publish update that will cause error
    await message_broker.publish('tag/update', {'tag': tag, 'value': 42.0})
    await asyncio.sleep(0.1)  # Allow time for error handling
    
    # Verify error was published
    error_handler.assert_called_once()
    error_data = error_handler.call_args[0][0]
    assert "Test error" in error_data["error"]
    assert error_data["topic"] == "tag/update"