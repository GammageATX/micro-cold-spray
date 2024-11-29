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

from micro_cold_spray.core.components.ui.managers.ui_update_manager import (
    UIUpdateManager, WidgetType, WidgetLocation
)

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
    async def test_widget_registration(self, ui_update_manager):
        """Test widget registration with type and location."""
        widget = MockWidget()
        widget_id = "test_widget"
        update_tags = ["motion.x.position", "motion.y.position"]
        
        await ui_update_manager.register_widget(
            widget_id=widget_id,
            update_tags=update_tags,
            widget_type=WidgetType.DISPLAY,
            location=WidgetLocation.MOTION,
            widget=widget
        )
        
        assert widget_id in ui_update_manager._widgets
        assert ui_update_manager._widgets[widget_id]["widget"] == widget
        assert ui_update_manager._widgets[widget_id]["type"] == WidgetType.DISPLAY
        assert ui_update_manager._widgets[widget_id]["location"] == WidgetLocation.MOTION
        assert ui_update_manager._widgets[widget_id]["tags"] == update_tags

    @pytest.mark.asyncio
    async def test_widget_cleanup_chain(self, ui_update_manager):
        """Test widget cleanup chain."""
        # Create parent widget with child
        parent = MockWidget()
        child = MockWidget()
        child.setParent(parent)
        
        # Register parent widget
        await ui_update_manager.register_widget(
            widget_id="parent",
            update_tags=["test.tag"],
            widget_type=WidgetType.WIDGET,
            location=WidgetLocation.MAIN,
            widget=parent
        )
        
        # Unregister parent should cleanup both widgets
        await ui_update_manager.unregister_widget("parent")
        
        # Verify cleanup called on both widgets
        parent.cleanup.assert_called_once()
        child.cleanup.assert_called_once()
        assert "parent" not in ui_update_manager._widgets

    @pytest.mark.asyncio
    async def test_tag_update_handling(self, ui_update_manager):
        """Test tag update handling with async gathering."""
        # Register multiple widgets for same tag
        widgets = [MockWidget() for _ in range(3)]
        tag = "motion.x.position"
        
        for i, widget in enumerate(widgets):
            await ui_update_manager.register_widget(
                widget_id=f"widget_{i}",
                update_tags=[tag],
                widget_type=WidgetType.MONITOR,
                location=WidgetLocation.DASHBOARD,
                widget=widget
            )
        
        # Send tag update
        update_data = {
            "tag": tag,
            "value": 100.0,
            "timestamp": datetime.now().isoformat()
        }
        await ui_update_manager._handle_tag_update(update_data)
        
        # Verify all widgets updated concurrently
        for widget in widgets:
            widget.update.assert_called_once_with(update_data)

    @pytest.mark.asyncio
    async def test_config_update_handling(self, ui_update_manager):
        """Test config update handling."""
        # Track UI updates
        updates = []
        async def collect_updates(data: Dict[str, Any]) -> None:
            updates.append(data)
        await ui_update_manager._message_broker.subscribe(
            "ui/update",
            collect_updates
        )
        
        # Send config update
        config_data = {
            "section": "process",
            "changes": {
                "parameters": {
                    "gas": {
                        "type": "helium"
                    }
                }
            }
        }
        await ui_update_manager._handle_config_update(config_data)
        await asyncio.sleep(0.1)
        
        # Verify UI update published
        assert len(updates) > 0
        assert updates[0]["type"] == "config"
        assert updates[0]["data"] == config_data
        assert "timestamp" in updates[0]

    @pytest.mark.asyncio
    async def test_widget_style_validation(self, ui_update_manager):
        """Test Qt6 style constant validation."""
        # Create widget with invalid style
        class InvalidWidget(QWidget):
            def __init__(self):
                super().__init__()
                # Use old-style constants (should fail)
                self.setAlignment(0x1)  # Invalid alignment
        
        widget = InvalidWidget()
        
        # Attempt to register should fail
        with pytest.raises(Exception) as exc:
            await ui_update_manager.register_widget(
                widget_id="invalid",
                update_tags=["test.tag"],
                widget_type=WidgetType.WIDGET,
                location=WidgetLocation.MAIN,
                widget=widget
            )
        assert "Must use Qt.AlignmentFlag.*" in str(exc.value)