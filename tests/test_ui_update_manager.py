"""UI Update Manager test suite.

Tests UI update management according to .cursorrules:
- Widget registration and cleanup
- Update routing
- Config update handling
- Error handling
- Async operations

UI Component Rules:
- Must register with UIUpdateManager
- Must implement update() method
- Must handle async operations
- Must cleanup on destroy
- Must use proper Qt6 constants

Run with:
    pytest tests/test_ui_update_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order

from PySide6.QtWidgets import QWidget, QFrame
from PySide6.QtCore import Qt

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager

class MockWidget(QWidget):
    """Mock widget for testing."""
    def __init__(self):
        super().__init__()
        self.update = AsyncMock()
        self.cleanup = AsyncMock()
        
        # Use proper Qt6 constants
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

@order(TestOrder.UI)
class TestUIUpdateManager:
    """UI update tests run last."""
    
    @pytest.mark.asyncio
    async def test_ui_update_manager_initialization(self, ui_update_manager):
        """Test UI update manager initialization."""
        assert ui_update_manager._is_initialized
        assert len(ui_update_manager._widgets) == 0

@pytest.mark.asyncio
async def test_ui_update_manager_register_widget(ui_update_manager):
    """Test widget registration."""
    widget = MockWidget()
    widget_id = "test_widget"
    
    await ui_update_manager.register_widget(widget_id, widget)
    assert widget_id in ui_update_manager._widgets
    assert ui_update_manager._widgets[widget_id] == widget

@pytest.mark.asyncio
async def test_ui_update_manager_handle_tag_update(ui_update_manager):
    """Test tag update handling."""
    # Register mock widget
    widget = MockWidget()
    widget_id = "test_widget"
    await ui_update_manager.register_widget(widget_id, widget)
    
    # Send tag update
    update_data = {
        "tag": "motion.x.position",  # Real tag from tags.yaml
        "value": 100.0,
        "timestamp": datetime.now().isoformat()
    }
    await ui_update_manager._handle_tag_update(update_data)
    
    # Verify widget update called
    widget.update.assert_called_once_with(update_data)

@pytest.mark.asyncio
async def test_ui_update_manager_handle_config_update(ui_update_manager):
    """Test config update handling."""
    # Register mock widget
    widget = MockWidget()
    widget_id = "test_widget"
    await ui_update_manager.register_widget(widget_id, widget)
    
    # Send config update
    update_data = {
        "config": "process",  # Real config from process.yaml
        "changes": {
            "parameters": {
                "gas": {
                    "type": "helium"
                }
            }
        },
        "timestamp": datetime.now().isoformat()
    }
    await ui_update_manager._handle_config_update(update_data)
    
    # Verify widget update called
    widget.update.assert_called_once_with(update_data)

@pytest.mark.asyncio
async def test_ui_update_manager_cleanup(ui_update_manager):
    """Test widget cleanup."""
    # Register mock widget
    widget = MockWidget()
    widget_id = "test_widget"
    await ui_update_manager.register_widget(widget_id, widget)
    
    # Unregister widget
    await ui_update_manager.unregister_widget(widget_id)
    
    # Verify cleanup called
    widget.cleanup.assert_called_once()
    assert widget_id not in ui_update_manager._widgets