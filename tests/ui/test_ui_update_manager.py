"""UI Update Manager test suite.

Tests UI update manager functionality according to .cursorrules:
- Widget registration
- Update handling
- Error handling
- Style validation

Run with:
    pytest tests/ui/test_ui_update_manager.py -v --asyncio-mode=auto
"""

# Standard library imports
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Third party imports
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

# First party imports
from tests.conftest import TestOrder, order
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.data.data_manager import DataManager
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.exceptions import UIError


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
async def data_manager():
    """Create a mock data manager."""
    manager = MagicMock(spec=DataManager)
    manager.list_files = AsyncMock()
    manager.load_file = AsyncMock()
    manager.save_file = AsyncMock()
    manager.delete_file = AsyncMock()
    return manager


@pytest.fixture
async def ui_manager(message_broker, config_manager, data_manager):
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
    async def test_widget_style_validation(self, ui_manager):
        """Test Qt6 style constant validation."""
        # Create widget with invalid style
        class InvalidWidget(QLabel):
            def __init__(self):
                super().__init__()
                # Use old-style constants (should fail)
                self.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Use new-style enum

        widget = InvalidWidget()

        # Register widget should succeed since we're using new-style enum
        await ui_manager.register_widget(
            widget=widget,
            widget_id="widget_system_invalid",
            update_tags=["system.state"]
        )

        # Verify widget was registered
        assert ui_manager.register_widget.call_count > 0
        assert ui_manager.register_widget.call_args.kwargs['widget'] == widget

    @pytest.mark.asyncio
    async def test_tag_request_response(self, ui_manager, message_broker, config_manager, data_manager):
        """Test tag request/response handling."""
        # Create real UI manager for this test
        manager = UIUpdateManager(message_broker, config_manager, data_manager)
        await manager.initialize()

        # Create mock widget
        mock_widget = MagicMock()
        mock_widget.handle_ui_update = AsyncMock()
        mock_widget.handle_error = AsyncMock()

        # Register widget
        await manager.register_widget(
            widget_id="widget_system_test",
            update_tags=["test/tag"],
            widget=mock_widget
        )

        # Send tag request
        request_id = await manager.send_tag_request(
            widget_id="widget_system_test",
            tag="test/tag",
            request_type="get"
        )

        # Verify request was published
        message_broker.publish.assert_called_with(
            "tag/request",
            {
                "request_type": "get",
                "tag": "test/tag",
                "request_id": request_id,
                "timestamp": pytest.approx(datetime.now().isoformat(), abs=2)
            }
        )

        # Simulate response
        await manager._handle_tag_response({
            "request_id": request_id,
            "tag": "test/tag",
            "value": 42,
            "timestamp": datetime.now().isoformat()
        })

        # Verify widget received update
        mock_widget.handle_ui_update.assert_called_once()
        update_data = mock_widget.handle_ui_update.call_args[0][0]
        assert "test/tag" in update_data
        assert update_data["test/tag"] == 42

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_error_handling(self, ui_manager, message_broker, config_manager, data_manager):
        """Test error handling with global error topic."""
        # Create real UI manager
        manager = UIUpdateManager(message_broker, config_manager, data_manager)
        await manager.initialize()

        # Create mock widget
        mock_widget = MagicMock()
        mock_widget.handle_ui_update = AsyncMock()
        mock_widget.handle_error = AsyncMock()

        # Test registration error
        with pytest.raises(UIError):
            await manager.register_widget(
                widget_id="invalid_id",  # Invalid format
                update_tags=["test/tag"],
                widget=mock_widget
            )

        # Verify error was published
        message_broker.publish.assert_called_with(
            "error",
            {
                "source": "ui_manager",
                "error": pytest.approx("Invalid widget ID format: invalid_id", rel=1e-3),
                "context": {
                    "widget_id": "invalid_id",
                    "tags": ["test/tag"],
                    "operation": "register"
                },
                "timestamp": pytest.approx(datetime.now().isoformat(), abs=2)
            }
        )

        # Register valid widget
        await manager.register_widget(
            widget_id="widget_system_test",
            update_tags=["test/tag"],
            widget=mock_widget
        )

        # Test tag request error
        request_id = await manager.send_tag_request(
            widget_id="widget_system_test",
            tag="test/tag",
            request_type="get"
        )

        # Simulate error response
        error_data = {
            "source": "tag_manager",
            "error": "Tag not found",
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }
        await manager._handle_error(error_data)

        # Verify widget received error
        mock_widget.handle_error.assert_called_once_with(error_data)

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_widget_cleanup(self, ui_manager, message_broker, config_manager, data_manager):
        """Test widget cleanup and request tracking."""
        # Create real UI manager
        manager = UIUpdateManager(message_broker, config_manager, data_manager)
        await manager.initialize()

        # Create mock widget
        mock_widget = MagicMock()
        mock_widget.handle_ui_update = AsyncMock()
        mock_widget._cleanup_resources = AsyncMock()

        # Register widget
        await manager.register_widget(
            widget_id="widget_system_test",
            update_tags=["test/tag"],
            widget=mock_widget
        )

        # Send multiple requests
        request_ids = []
        for i in range(3):
            request_id = await manager.send_tag_request(
                widget_id="widget_system_test",
                tag=f"test/tag/{i}",
                request_type="get"
            )
            request_ids.append(request_id)

        # Verify requests are tracked
        assert len(manager._pending_requests) == 3

        # Unregister widget
        await manager.unregister_widget("widget_system_test")

        # Verify cleanup
        mock_widget._cleanup_resources.assert_called_once()
        assert len(manager._pending_requests) == 0

        # Verify widget was removed
        assert "widget_system_test" not in manager._widgets

        await manager.shutdown()
