"""Dashboard Tab test suite.

Run with:
    pytest tests/test_dashboard_tab.py -v --asyncio-mode=auto -s

Tests the DashboardTab widget according to .cursorrules:
- Widget initialization and cleanup
- UI update handling
- Child widget management
- Error handling
- Async operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import logging
import asyncio

from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication

from micro_cold_spray.core.components.ui.tabs.dashboard_tab import DashboardTab
from micro_cold_spray.core.components.ui.widgets.sequence.sequence_control import SequenceControl
from micro_cold_spray.core.components.ui.widgets.sequence.progress_display import ProgressDisplay
from micro_cold_spray.core.components.ui.widgets.data.data_widget import DataWidget
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager

from tests.conftest import TestOrder, order

# Setup test logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@pytest.fixture(scope="session")
def qapp():
    """Create the QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class MockQWidget(QWidget):
    """Base mock widget for testing."""
    def __init__(self, parent=None):
        """Initialize with async methods."""
        super().__init__(parent)
        self.cleanup = AsyncMock()
        self.handle_ui_update = AsyncMock()
        self.setLayout(QVBoxLayout())
        self._widget_id = None
        logger.debug(f"MockQWidget initialized: {self}")

    @property
    def widget_id(self):
        """Get widget ID."""
        return self._widget_id

    @widget_id.setter
    def widget_id(self, value):
        """Set widget ID."""
        self._widget_id = value


class MockBaseWidget(MockQWidget):
    """Mock for BaseWidget with required async methods."""
    def __init__(self, widget_id: str, ui_manager: UIUpdateManager, parent=None):
        """Initialize with widget ID and UI manager."""
        super().__init__(parent)
        self.widget_id = widget_id
        self._ui_manager = ui_manager
        logger.debug(f"MockBaseWidget initialized: {widget_id}")


@pytest.fixture
async def ui_manager():
    """Create a mock UI manager."""
    manager = MagicMock(spec=UIUpdateManager)
    manager.register_widget = AsyncMock()
    manager.unregister_widget = AsyncMock()
    logger.debug("Mock UI manager created")
    return manager


@pytest.fixture
async def dashboard_with_mocks(qapp, ui_manager):
    """Create a dashboard with mocked child widgets."""
    seq_path = 'micro_cold_spray.core.components.ui.tabs.dashboard_tab.SequenceControl'
    prog_path = 'micro_cold_spray.core.components.ui.tabs.dashboard_tab.ProgressDisplay'
    data_path = 'micro_cold_spray.core.components.ui.tabs.dashboard_tab.DataWidget'
    base_widget_path = 'micro_cold_spray.core.components.ui.widgets.base_widget.BaseWidget'

    logger.debug("Setting up mock widgets")
    with patch(seq_path) as mock_seq, \
            patch(prog_path) as mock_prog, \
            patch(data_path) as mock_data, \
            patch(base_widget_path) as mock_base:

        # Create mock widgets that properly inherit from QWidget
        mock_seq_widget = MockQWidget()
        mock_prog_widget = MockQWidget()
        mock_data_widget = MockQWidget()

        # Setup mock widget classes with proper update handling
        mock_seq.return_value = mock_seq_widget
        mock_seq.return_value.__class__ = SequenceControl
        mock_seq.return_value.cleanup = AsyncMock()
        mock_seq.return_value.handle_ui_update = AsyncMock()
        mock_seq_widget._widget_id = "control_dashboard_sequence"

        mock_prog.return_value = mock_prog_widget
        mock_prog.return_value.__class__ = ProgressDisplay
        mock_prog.return_value.cleanup = AsyncMock()
        mock_prog.return_value.handle_ui_update = AsyncMock()
        mock_prog_widget._widget_id = "display_dashboard_progress"

        mock_data.return_value = mock_data_widget
        mock_data.return_value.__class__ = DataWidget
        mock_data.return_value.cleanup = AsyncMock()
        mock_data.return_value.handle_ui_update = AsyncMock()
        mock_data_widget._widget_id = "widget_dashboard_data"

        # Setup base widget to handle registration
        mock_base.return_value = MockBaseWidget("tab_dashboard", ui_manager)
        mock_base.return_value.cleanup = AsyncMock()
        mock_base.return_value.handle_ui_update = AsyncMock()

        logger.debug("Mock widgets created")

        # Create dashboard with mocked widgets
        logger.debug("Creating dashboard tab")
        dashboard = DashboardTab(ui_manager=ui_manager)
        logger.debug("Dashboard tab created")

        # Wait for async initialization
        await asyncio.sleep(0.1)  # Allow time for async initialization

        # Return the actual mock widget instances for update testing
        yield dashboard, mock_seq_widget, mock_prog_widget, mock_data_widget


@order(TestOrder.UI)
class TestDashboardTab:
    """Dashboard tab tests."""

    @pytest.mark.asyncio
    async def test_dashboard_initialization(self, qapp, ui_manager):
        """Test dashboard tab initialization."""
        logger.debug("Starting dashboard initialization test")

        # Create dashboard tab with mocked QWidget base
        with patch('micro_cold_spray.core.components.ui.widgets.base_widget.QWidget', MockQWidget):
            logger.debug("Creating dashboard tab")
            dashboard = DashboardTab(ui_manager=ui_manager)
            logger.debug("Dashboard tab created")

            # Wait for async initialization
            await asyncio.sleep(0.1)  # Allow time for async initialization

            # Verify all widgets were registered
            assert ui_manager.register_widget.call_count == 4

            # Verify dashboard registration
            dashboard_call = [call for call in ui_manager.register_widget.call_args_list
                              if call[1]['widget_id'] == 'tab_dashboard'][0]
            assert 'sequence.loaded' in dashboard_call[1]['update_tags']
            assert 'sequence.state' in dashboard_call[1]['update_tags']

            # Verify sequence control registration
            seq_call = [call for call in ui_manager.register_widget.call_args_list
                        if call[1]['widget_id'] == 'control_dashboard_sequence'][0]
            assert 'sequence.state' in seq_call[1]['update_tags']
            assert 'sequence.progress' in seq_call[1]['update_tags']

            # Verify dashboard was created and initialized
            assert isinstance(dashboard, DashboardTab)
            assert dashboard.widget_id == 'tab_dashboard'

    @pytest.mark.asyncio
    async def test_ui_update_handling(self, dashboard_with_mocks):
        """Test UI update handling."""
        dashboard, seq_control, prog_display, data_widget = dashboard_with_mocks
        logger.debug("Starting UI update test")

        # Test system state update
        state_data = {
            "system.state": "RUNNING",
            "timestamp": datetime.now().isoformat()
        }
        await dashboard.handle_ui_update(state_data)
        logger.debug("System state update handled")

        # Test system message update
        message_data = {
            "system.message": "Test message",
            "timestamp": datetime.now().isoformat()
        }
        await dashboard.handle_ui_update(message_data)
        logger.debug("System message update handled")

        # Test error handling with invalid data
        invalid_data = {"invalid_key": "value"}
        await dashboard.handle_ui_update(invalid_data)  # Should not raise
        logger.debug("Invalid data handled without error")

    @pytest.mark.asyncio
    async def test_cleanup_chain(self, dashboard_with_mocks):
        """Test cleanup chain execution."""
        dashboard, seq_control, prog_display, data_widget = dashboard_with_mocks
        logger.debug("Starting cleanup chain test")

        # Perform cleanup
        await dashboard.cleanup()
        logger.debug("Cleanup completed")

        # Verify all child widgets cleaned up
        seq_control.cleanup.assert_called_once()
        prog_display.cleanup.assert_called_once()
        data_widget.cleanup.assert_called_once()
        logger.debug("Child widget cleanup verified")

    @pytest.mark.asyncio
    async def test_error_handling(self, dashboard_with_mocks):
        """Test error handling during updates."""
        dashboard, seq_control, prog_display, data_widget = dashboard_with_mocks
        logger.debug("Starting error handling test")

        # Mock error in child widget
        seq_control.handle_ui_update.side_effect = Exception("Test error")
        logger.debug("Mocked error in sequence control")

        # Send update that would trigger child widget
        update_data = {
            "sequence.state": "ERROR",
            "error": "Test error condition"
        }

        # Should handle error without raising
        await dashboard.handle_ui_update(update_data)
        logger.debug("Error handled without raising")

    @pytest.mark.asyncio
    async def test_child_widget_updates(self, dashboard_with_mocks):
        """Test update propagation to child widgets."""
        dashboard, seq_control, prog_display, data_widget = dashboard_with_mocks
        logger.debug("Starting child widget update test")

        # Test sequence state update
        sequence_data = {
            "sequence.state": "RUNNING",
            "step": "test_step",
            "progress": 50
        }
        await dashboard.handle_ui_update(sequence_data)
        logger.debug("Update sent to child widgets")

        # Wait for async update propagation
        await asyncio.sleep(0.1)  # Allow time for async updates

        # Verify child widgets received updates
        seq_control.handle_ui_update.assert_called_once_with(sequence_data)
        prog_display.handle_ui_update.assert_called_once_with(sequence_data)
        logger.debug("Child widget updates verified")
