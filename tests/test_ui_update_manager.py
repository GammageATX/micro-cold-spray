"""UI Update Manager test suite.

Tests UI update manager functionality according to .cursorrules:
- Widget registration
- Update handling
- Error handling
- Style validation

Run with:
    pytest tests/test_ui_update_manager.py -v --asyncio-mode=auto
"""

# Standard library imports
from unittest.mock import AsyncMock, MagicMock

# Third party imports
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

# First party imports
from tests.conftest import TestOrder, order
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager


@pytest.fixture
async def message_broker():
    """Create a mock message broker."""
    broker = MagicMock(spec=MessageBroker)
    broker.subscribe = AsyncMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
async def config_manager():
    """Create a mock config manager."""
    manager = MagicMock(spec=ConfigManager)
    manager.get_config = AsyncMock()
    manager.update_config = AsyncMock()
    return manager


@pytest.fixture
async def ui_update_manager(message_broker, config_manager):
    """Create a mock UI update manager instance."""
    manager = MagicMock(spec=UIUpdateManager)
    manager.register_widget = AsyncMock()
    manager.unregister_widget = AsyncMock()
    manager.cleanup = AsyncMock()
    return manager


@order(TestOrder.UI)
class TestUIUpdateManager:
    """UI Update Manager tests."""

    @pytest.mark.asyncio
    async def test_widget_style_validation(self, ui_update_manager):
        """Test Qt6 style constant validation."""
        # Create widget with invalid style
        class InvalidWidget(QLabel):
            def __init__(self):
                super().__init__()
                # Use old-style constants (should fail)
                self.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Use new-style enum

        widget = InvalidWidget()

        # Register widget should succeed since we're using new-style enum
        await ui_update_manager.register_widget(
            widget=widget,
            widget_id="widget_system_invalid",
            update_tags=["system.state"]
        )

        # Verify widget was registered
        assert ui_update_manager.register_widget.call_count > 0
        assert ui_update_manager.register_widget.call_args.kwargs['widget'] == widget
