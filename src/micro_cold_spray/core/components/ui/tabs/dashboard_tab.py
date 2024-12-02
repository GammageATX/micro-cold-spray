"""Dashboard tab for system monitoring."""
import logging

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ..managers.ui_update_manager import UIUpdateManager

# Import base widget first
from ..widgets.base_widget import BaseWidget
from ..widgets.data.data_widget import DataWidget
from ..widgets.sequence.progress_display import ProgressDisplay

# Import widgets after base imports
from ..widgets.sequence.sequence_control import SequenceControl

logger = logging.getLogger(__name__)


class DashboardTab(BaseWidget):
    """Main dashboard tab for system overview."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        # Initialize with proper widget ID
        super().__init__(
            widget_id="tab_dashboard",
            ui_manager=ui_manager,
            update_tags=[
                "sequence.loaded",
                "sequence.state",
                "system.state",
                "system.message"
            ],
            parent=parent
        )

        # Store child widget references
        self._sequence_control = None
        self._progress_display = None
        self._data_widget = None

        self._init_ui()
        logger.info("Dashboard tab initialized")

    def _init_ui(self):
        """Initialize the dashboard UI."""
        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        # Add header
        header = QLabel("System Dashboard")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(header)

        # Sequence Control Section
        sequence_frame = QFrame()
        sequence_frame.setFrameShape(QFrame.Shape.StyledPanel)
        sequence_frame.setFrameShadow(QFrame.Shadow.Raised)
        sequence_layout = QVBoxLayout()
        sequence_layout.setContentsMargins(10, 10, 10, 10)

        # Add Sequence Control widget
        self._sequence_control = SequenceControl(self._ui_manager)
        sequence_layout.addWidget(self._sequence_control)

        # Add Progress Display widget
        self._progress_display = ProgressDisplay(self._ui_manager)
        sequence_layout.addWidget(self._progress_display)

        sequence_frame.setLayout(sequence_layout)
        main_layout.addWidget(sequence_frame)

        # Create horizontal layout for monitoring widgets
        monitor_layout = QHBoxLayout()
        monitor_layout.setSpacing(10)

        # Add Data Widget
        self._data_widget = DataWidget(self._ui_manager)
        monitor_layout.addWidget(self._data_widget)

        # Add monitor layout to main layout
        main_layout.addLayout(monitor_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    async def handle_ui_update(self, data: dict) -> None:
        """Handle UI updates from UIUpdateManager."""
        try:
            # Propagate updates to child widgets
            if self._sequence_control:
                await self._sequence_control.handle_ui_update(data)
            if self._progress_display:
                await self._progress_display.handle_ui_update(data)
            if self._data_widget:
                await self._data_widget.handle_ui_update(data)

            # Handle dashboard-specific updates
            if "system.state" in data:
                state = data["system.state"]
                logger.debug(
                    f"Dashboard received system state update: {state}")
                # Update tab state if needed

            elif "system.message" in data:
                message = data["system.message"]
                logger.debug(f"Dashboard received system message: {message}")
                # Update tab message if needed

        except Exception as e:
            logger.error(f"Error handling UI update in DashboardTab: {e}")
            await self.send_update("system.error", f"Dashboard error: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clean up child widgets first
            if hasattr(
                    self,
                    '_sequence_control') and self._sequence_control is not None:
                if hasattr(
                        self._sequence_control,
                        'cleanup') and callable(
                        self._sequence_control.cleanup):
                    await self._sequence_control.cleanup()

            if hasattr(
                    self,
                    '_progress_display') and self._progress_display is not None:
                if hasattr(
                        self._progress_display,
                        'cleanup') and callable(
                        self._progress_display.cleanup):
                    await self._progress_display.cleanup()

            if hasattr(self, '_data_widget') and self._data_widget is not None:
                if hasattr(
                        self._data_widget,
                        'cleanup') and callable(
                        self._data_widget.cleanup):
                    await self._data_widget.cleanup()

            # Then clean up base widget
            await super(DashboardTab, self).cleanup()

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
