"""Main application window."""
from datetime import datetime
from typing import Any, Dict
import asyncio

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from micro_cold_spray.core.exceptions import UIError
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.ui.tabs.config_tab import ConfigTab
from micro_cold_spray.core.ui.tabs.dashboard_tab import DashboardTab
from micro_cold_spray.core.ui.tabs.diagnostics_tab import DiagnosticsTab
from micro_cold_spray.core.ui.tabs.editor_tab import EditorTab
from micro_cold_spray.core.ui.tabs.motion_tab import MotionTab
from micro_cold_spray.core.ui.widgets.base_widget import BaseWidget
from micro_cold_spray.core.ui.widgets.status.connection_status import ConnectionStatus


class SystemStateDisplay(BaseWidget):
    """Widget for displaying system state."""

    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        """Initialize with required dependencies."""
        super().__init__(
            widget_id="widget_system_state",
            ui_manager=ui_manager,
            update_tags=["state/change"],
            parent=parent
        )
        self.label = QLabel("System: NONE")
        self.label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.label.setFixedWidth(120)
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "state/change" in data:
                state_data = data["state/change"]
                if state_data.get("type") == "system":
                    state = state_data.get("state", "NONE")
                    self.label.setText(f"System: {state}")

                    # Add color coding for different states
                    color = {
                        "CONNECTED": "#2ecc71",    # Green
                        "DISCONNECTED": "#e74c3c",  # Red
                        "NONE": "#f1c40f",         # Yellow
                        "ERROR": "#e74c3c"         # Red
                    }.get(state, "#2c3e50")        # Default dark gray

                    self.label.setStyleSheet(f"font-weight: bold; color: {color};")
                    logger.debug(f"Updated system state display: {state}")

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")


class SystemMessageDisplay(BaseWidget):
    """Widget for displaying system messages."""

    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        """Initialize with required dependencies."""
        super().__init__(
            widget_id="widget_system_message",
            ui_manager=ui_manager,
            update_tags=["ui/state"],
            parent=parent
        )
        self.label = QLabel("System starting...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "ui/state" in data:
                state_data = data["ui/state"]
                if state_data.get("type") == "system.message":
                    message = state_data.get("state", {}).get("message", "")
                    self.label.setText(message)
        except Exception as e:
            logger.error(f"Error handling system message update: {e}")


class SystemErrorDisplay(BaseWidget):
    """Widget for displaying system errors."""

    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        """Initialize with required dependencies."""
        super().__init__(
            widget_id="widget_system_error",
            ui_manager=ui_manager,
            update_tags=["error"],
            parent=parent
        )
        self.label = QLabel("No errors")
        self.label.setStyleSheet("color: #27ae60;")
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "error" in data:
                error_data = data["error"]
                error_msg = error_data.get("error", "Unknown error")
                self.label.setText(error_msg)
                self.label.setStyleSheet("color: #e74c3c;")
        except Exception as e:
            logger.error(f"Error handling error update: {e}")


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(
        self,
        config_manager: ConfigManager,
        message_broker: MessageBroker,
        ui_manager: UIUpdateManager,
        tag_manager: TagManager,
        ui_config: Dict[str, Any]
    ) -> None:
        """Initialize with required dependencies."""
        super().__init__()

        self._config = ui_config

        # Validate dependencies
        if not all([config_manager, message_broker, ui_manager, tag_manager]):
            logger.error("Missing required dependencies")
            raise UIError("Missing required dependencies")

        # Store dependencies
        self._config_manager = config_manager
        self._message_broker = message_broker
        self._ui_manager = ui_manager
        self._tag_manager = tag_manager

        # Track window state
        self.is_closing = False
        self._is_initialized = False

        # Initialize UI
        self._init_ui()
        logger.info("MainWindow initialized")

    async def initialize(self) -> None:
        """Initialize main window."""
        try:
            if self._is_initialized:
                return

            # Initialize all tabs
            await self.dashboard_tab.initialize()
            await self.motion_tab.initialize()
            await self.editor_tab.initialize()
            await self.config_tab.initialize()
            await self.diagnostics_tab.initialize()

            # Subscribe to state changes
            await self._message_broker.subscribe(
                "state/change",
                self._handle_state_change
            )

            self._is_initialized = True
            logger.info("MainWindow initialization complete")

        except Exception as e:
            error_context = {
                "window": "MainWindow",
                "operation": "initialize",
                "timestamp": datetime.now().isoformat()
            }
            logger.exception("Failed to initialize MainWindow")
            raise UIError(
                "MainWindow initialization failed",
                error_context) from e

    async def _handle_state_change(self, data: Dict[str, Any]) -> None:
        """Handle state change messages."""
        try:
            state_type = data.get("type")
            state = data.get("state")
            if state_type == "system":
                # Update window title based on system state
                title = self._config.get("title", "Micro Cold Spray")
                if state != "CONNECTED":
                    title += f" ({state})"
                self.setWindowTitle(title)

        except Exception as e:
            logger.error(f"Error handling state change: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "source": "main_window",
                    "error": str(e),
                    "context": "state_change",
                    "timestamp": datetime.now().isoformat()
                }
            )

    def _init_ui(self) -> None:
        """Initialize the main window UI."""
        try:
            # Use config for window setup
            geometry = self._config.get("geometry", {})
            self.setGeometry(
                geometry.get("x", 100),
                geometry.get("y", 100),
                geometry.get("width", 1280),
                geometry.get("height", 800)
            )
            self.setWindowTitle(self._config.get("title", "Micro Cold Spray"))

            # Use config for style
            style = self._config.get("style", {})
            font = style.get("font", {})
            if font:
                self.setStyleSheet(f"""
                    * {{
                        font-family: {font.get("family", "Segoe UI")};
                        font-size: {font.get("size", 10)}px;
                    }}
                """)

            # Create central widget and main layout
            central_widget = QWidget()
            main_layout = QVBoxLayout()
            central_widget.setLayout(main_layout)
            self.setCentralWidget(central_widget)

            # Create status bar
            status_bar = QStatusBar()
            self.setStatusBar(status_bar)

            # Add system state widgets to status bar
            status_frame = QFrame()
            status_layout = QHBoxLayout()
            status_frame.setLayout(status_layout)

            # System state display
            self.system_state = SystemStateDisplay(self._ui_manager)
            status_layout.addWidget(self.system_state)

            # Connection status
            self.connection_status = ConnectionStatus(
                self._ui_manager,
                self._message_broker,
                self._config_manager
            )
            status_layout.addWidget(self.connection_status)

            # System message display
            self.system_message = SystemMessageDisplay(self._ui_manager)
            status_layout.addWidget(self.system_message)

            # System error display
            self.system_error = SystemErrorDisplay(self._ui_manager)
            status_layout.addWidget(self.system_error)

            status_bar.addWidget(status_frame)

            # Create tab widget
            self.tab_widget = QTabWidget()
            main_layout.addWidget(self.tab_widget)

            # Create tabs
            self.dashboard_tab = DashboardTab(
                self._ui_manager,
                self._message_broker,
                self._config_manager,
                parent=self.tab_widget
            )
            self.motion_tab = MotionTab(
                self._ui_manager,
                self._message_broker,
                parent=self.tab_widget
            )
            self.editor_tab = EditorTab(
                self._ui_manager,
                self._message_broker,
                self._config_manager,
                parent=self.tab_widget
            )
            self.config_tab = ConfigTab(
                self._ui_manager,
                parent=self.tab_widget
            )
            self.diagnostics_tab = DiagnosticsTab(
                self._ui_manager,
                parent=self.tab_widget
            )

            # Add tabs in order from config
            layout = self._config.get("layout", {}).get("main", [])
            for tab_name in layout:
                if tab_name == "dashboard":
                    self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
                elif tab_name == "motion":
                    self.tab_widget.addTab(self.motion_tab, "Motion")
                elif tab_name == "editor":
                    self.tab_widget.addTab(self.editor_tab, "Editor")
                elif tab_name == "config":
                    self.tab_widget.addTab(self.config_tab, "Config")
                elif tab_name == "diagnostics":
                    self.tab_widget.addTab(self.diagnostics_tab, "Diagnostics")

            logger.info("UI initialization complete")

        except Exception as e:
            logger.error(f"Error initializing UI: {e}")
            raise UIError("Failed to initialize UI") from e

    async def cleanup(self) -> None:
        """Clean up resources before closing."""
        try:
            # Set closing flag
            self.is_closing = True

            # Clean up tabs
            await self.dashboard_tab.cleanup()
            await self.motion_tab.cleanup()
            await self.editor_tab.cleanup()
            await self.config_tab.cleanup()
            await self.diagnostics_tab.cleanup()

            # Unsubscribe from state changes
            await self._message_broker.unsubscribe("state/change", self._handle_state_change)

            logger.info("MainWindow cleanup complete")

        except Exception as e:
            logger.error(f"Error during MainWindow cleanup: {e}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        # Set closing flag immediately
        self.is_closing = True
        
        # Accept the event immediately to avoid Qt deleting it
        event.accept()
        
        # Create cleanup task
        cleanup_task = asyncio.create_task(self.cleanup())
        
        # Add callback just to log any cleanup errors
        def cleanup_done(task):
            try:
                task.result()  # Get result to handle any exceptions
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        
        cleanup_task.add_done_callback(cleanup_done)
