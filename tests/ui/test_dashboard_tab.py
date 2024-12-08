"""Dashboard Tab test suite.

Tests dashboard tab functionality according to .cursorrules:
- Widget initialization
- UI updates
- State handling
- Error handling

Run with:
    pytest tests/ui/test_dashboard_tab.py -v --asyncio-mode=auto
"""

# Standard library imports
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

# Third party imports
import pytest
from PySide6.QtWidgets import QWidget
from loguru import logger

# First party imports
from tests.conftest import TestOrder, order
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.components.ui.tabs.dashboard_tab import DashboardTab

# Constants for patching
SEQUENCE_CONTROL_PATH = 'micro_cold_spray.core.components.ui.widgets.sequence.sequence_control.SequenceControl'
PROGRESS_DISPLAY_PATH = 'micro_cold_spray.core.components.ui.widgets.sequence.progress_display.ProgressDisplay'
DATA_WIDGET_PATH = 'micro_cold_spray.core.components.ui.widgets.data.data_widget.DataWidget'
BASE_WIDGET_PATH = 'micro_cold_spray.core.components.ui.widgets.base_widget.QWidget'


class MockQWidget(QWidget):
    """Mock QWidget for testing."""
    def __init__(self):
        super().__init__()
        self.cleanup = AsyncMock()
        self.handle_ui_update = AsyncMock()
        self.widget_id = "mock_widget"


@pytest.fixture
def mock_sequence_control(ui_manager):
    """Create a mock sequence control widget."""
    mock = MagicMock()
    mock.cleanup = AsyncMock()
    mock.handle_ui_update = AsyncMock()
    mock.widget_id = "control_dashboard_sequence"
    mock._ui_manager = ui_manager
    return mock


@pytest.fixture
def mock_progress_display(ui_manager):
    """Create a mock progress display widget."""
    mock = MagicMock()
    mock.cleanup = AsyncMock()
    mock.handle_ui_update = AsyncMock()
    mock.widget_id = "display_dashboard_progress"
    mock._ui_manager = ui_manager
    return mock


@pytest.fixture
def mock_data_widget(ui_manager):
    """Create a mock data widget."""
    mock = MagicMock()
    mock.cleanup = AsyncMock()
    mock.handle_ui_update = AsyncMock()
    mock.widget_id = "widget_dashboard_data"
    mock._ui_manager = ui_manager
    return mock


@pytest.fixture
async def ui_manager():
    """Create a mock UI manager."""
    manager = MagicMock(spec=UIUpdateManager)
    manager.register_widget = AsyncMock()
    manager.unregister_widget = AsyncMock()
    return manager


@order(TestOrder.UI)
class TestDashboardTab:
    """Dashboard tab tests."""

    @pytest.mark.asyncio
    async def test_dashboard_initialization(
        self, qapp, ui_manager, mock_sequence_control, mock_progress_display, mock_data_widget
    ):  # pylint: disable=unused-argument
        """Test dashboard tab initialization."""
        logger.debug("Starting dashboard initialization test")

        # Create dashboard tab with mocked QWidget base
        with patch(BASE_WIDGET_PATH, MockQWidget), \
             patch(SEQUENCE_CONTROL_PATH, return_value=mock_sequence_control), \
             patch(PROGRESS_DISPLAY_PATH, return_value=mock_progress_display), \
             patch(DATA_WIDGET_PATH, return_value=mock_data_widget):

            logger.debug("Creating dashboard tab")
            dashboard_widget = DashboardTab(ui_manager=ui_manager)
            logger.debug("Dashboard tab created")

            # Wait for async initialization
            await asyncio.sleep(0.1)

            # Verify widget was created properly
            assert isinstance(dashboard_widget, DashboardTab)
            assert dashboard_widget._ui_manager == ui_manager

            # Verify dashboard registration
            registration_call = ui_manager.register_widget.call_args_list[0]
            assert registration_call.kwargs['widget_id'] == 'tab_dashboard'
            assert registration_call.kwargs['update_tags'] == [
                'sequence.loaded',
                'sequence.state',
                'system.state',
                'system.message'
            ]

    @pytest.mark.asyncio
    async def test_ui_update_handling(
        self, qapp, ui_manager, mock_sequence_control, mock_progress_display, mock_data_widget
    ):  # pylint: disable=unused-argument
        """Test UI update handling."""
        # Create dashboard tab with mocked QWidget base
        with patch(BASE_WIDGET_PATH, MockQWidget), \
             patch(SEQUENCE_CONTROL_PATH, return_value=mock_sequence_control), \
             patch(PROGRESS_DISPLAY_PATH, return_value=mock_progress_display), \
             patch(DATA_WIDGET_PATH, return_value=mock_data_widget):

            dashboard_widget = DashboardTab(ui_manager=ui_manager)
            await asyncio.sleep(0.1)  # Allow time for async initialization

            # Send test update
            test_update = {
                "tag": "state.system",
                "value": "ready",
                "timestamp": datetime.now().isoformat()
            }
            await dashboard_widget.handle_ui_update(test_update)

            # Verify update handled
            assert dashboard_widget._sequence_control.handle_ui_update.call_count > 0
            assert dashboard_widget._progress_display.handle_ui_update.call_count > 0
            assert dashboard_widget._data_widget.handle_ui_update.call_count > 0

    @pytest.mark.asyncio
    async def test_cleanup_chain(
        self, qapp, ui_manager, mock_sequence_control, mock_progress_display, mock_data_widget
    ):  # pylint: disable=unused-argument
        """Test cleanup chain."""
        # Create dashboard tab with mocked QWidget base
        with patch(BASE_WIDGET_PATH, MockQWidget), \
             patch(SEQUENCE_CONTROL_PATH, return_value=mock_sequence_control), \
             patch(PROGRESS_DISPLAY_PATH, return_value=mock_progress_display), \
             patch(DATA_WIDGET_PATH, return_value=mock_data_widget):

            dashboard_widget = DashboardTab(ui_manager=ui_manager)
            await asyncio.sleep(0.1)  # Allow time for async initialization

            # Call cleanup
            await dashboard_widget.cleanup()

            # Verify cleanup chain
            assert dashboard_widget._sequence_control.cleanup.call_count > 0
            assert dashboard_widget._progress_display.cleanup.call_count > 0
            assert dashboard_widget._data_widget.cleanup.call_count > 0

    @pytest.mark.asyncio
    async def test_error_handling(
        self, qapp, ui_manager, mock_sequence_control, mock_progress_display, mock_data_widget
    ):  # pylint: disable=unused-argument
        """Test error handling."""
        # Create dashboard tab with mocked QWidget base
        with patch(BASE_WIDGET_PATH, MockQWidget), \
             patch(SEQUENCE_CONTROL_PATH, return_value=mock_sequence_control), \
             patch(PROGRESS_DISPLAY_PATH, return_value=mock_progress_display), \
             patch(DATA_WIDGET_PATH, return_value=mock_data_widget):

            dashboard_widget = DashboardTab(ui_manager=ui_manager)
            await asyncio.sleep(0.1)  # Allow time for async initialization

            # Send test error
            test_error = {
                "tag": "state.system",
                "error": "Test error",
                "timestamp": datetime.now().isoformat()
            }
            await dashboard_widget.handle_ui_update(test_error)

            # Verify error handled
            assert dashboard_widget._sequence_control.handle_ui_update.call_count > 0
            assert dashboard_widget._progress_display.handle_ui_update.call_count > 0
            assert dashboard_widget._data_widget.handle_ui_update.call_count > 0

    @pytest.mark.asyncio
    async def test_child_widget_updates(
        self, qapp, ui_manager, mock_sequence_control, mock_progress_display, mock_data_widget
    ):  # pylint: disable=unused-argument
        """Test child widget updates."""
        # Create dashboard tab with mocked QWidget base
        with patch(BASE_WIDGET_PATH, MockQWidget), \
             patch(SEQUENCE_CONTROL_PATH, return_value=mock_sequence_control), \
             patch(PROGRESS_DISPLAY_PATH, return_value=mock_progress_display), \
             patch(DATA_WIDGET_PATH, return_value=mock_data_widget):

            dashboard_widget = DashboardTab(ui_manager=ui_manager)
            await asyncio.sleep(0.1)  # Allow time for async initialization

            # Send test updates
            test_updates = [
                {
                    "tag": "sequence.progress",
                    "value": 50.0,
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "tag": "sequence.state",
                    "value": "running",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "tag": "data.history",
                    "value": {"test": "data"},
                    "timestamp": datetime.now().isoformat()
                }
            ]

            for update in test_updates:
                await dashboard_widget.handle_ui_update(update)

            # Verify updates forwarded to child widgets
            assert dashboard_widget._sequence_control.handle_ui_update.call_count > 0
            assert dashboard_widget._progress_display.handle_ui_update.call_count > 0
            assert dashboard_widget._data_widget.handle_ui_update.call_count > 0
