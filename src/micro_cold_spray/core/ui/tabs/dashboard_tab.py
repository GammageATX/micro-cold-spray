"""Dashboard tab for system monitoring."""
import logging

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ..managers.ui_update_manager import UIUpdateManager
from ...infrastructure.messaging.message_broker import MessageBroker
from ...infrastructure.config.config_manager import ConfigManager

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
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        parent=None
    ):
        # Initialize with proper widget ID
        super().__init__(
            widget_id="tab_dashboard",
            ui_manager=ui_manager,
            update_tags=[
                "sequence/loaded",
                "sequence/state",
                "system/state",
                "system/message",
                "system/error"
            ],
            parent=parent
        )

        # Store dependencies
        self._message_broker = message_broker
        self._config_manager = config_manager

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
        self._sequence_control = SequenceControl(self._ui_manager, self._message_broker, parent=self)
        sequence_layout.addWidget(self._sequence_control)

        # Add Progress Display widget
        self._progress_display = ProgressDisplay(self._ui_manager, self._message_broker, parent=self)
        sequence_layout.addWidget(self._progress_display)

        sequence_frame.setLayout(sequence_layout)
        main_layout.addWidget(sequence_frame)

        # Create horizontal layout for monitoring widgets
        monitor_layout = QHBoxLayout()
        monitor_layout.setSpacing(10)

        # Add Data Widget
        self._data_widget = DataWidget(
            self._ui_manager,
            self._message_broker,
            self._config_manager,
            parent=self
        )
        monitor_layout.addWidget(self._data_widget)

        # Add monitor layout to main layout
        main_layout.addLayout(monitor_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    async def _initialize(self) -> None:
        """Initialize child widgets."""
        try:
            # Initialize child widgets
            if self._sequence_control:
                await self._sequence_control.initialize()
            if self._progress_display:
                await self._progress_display.initialize()
            if self._data_widget:
                await self._data_widget.initialize()

            logger.info("Dashboard tab child widgets initialized")

        except Exception as e:
            logger.error(f"Error initializing dashboard tab child widgets: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "dashboard_tab",
                    "message": f"Failed to initialize child widgets: {e}",
                    "level": "error"
                }
            )
            raise

    async def handle_ui_update(self, data: dict) -> None:
        """Handle UI updates from UIUpdateManager."""
        try:
            # Extract topic and message
            topic, message = next(iter(data.items()))

            # Only propagate relevant updates to child widgets
            if topic in ["sequence/loaded", "sequence/state"]:
                if self._sequence_control:
                    await self._sequence_control.handle_ui_update(data)
                if self._progress_display:
                    await self._progress_display.handle_ui_update(data)
            elif topic in ["data/response", "data/state"]:
                if self._data_widget:
                    await self._data_widget.handle_ui_update(data)
            elif topic == "system/state":
                # Update all widgets for system state changes
                for widget in [self._sequence_control, self._progress_display, self._data_widget]:
                    if widget:
                        await widget.handle_ui_update(data)
            elif topic == "system/error":
                logger.error(f"Dashboard received error: {message}")

        except Exception as e:
            logger.error(f"Error handling UI update in DashboardTab: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "dashboard_tab",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clean up child widgets first
            child_widgets = [
                self._sequence_control,
                self._progress_display,
                self._data_widget
            ]

            for widget in child_widgets:
                if widget is not None and hasattr(widget, 'cleanup'):
                    try:
                        await widget.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up widget {widget.widget_id}: {e}")

            # Then clean up base widget
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Don't re-raise to allow other cleanup to continue
