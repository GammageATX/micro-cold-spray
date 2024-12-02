"""Main application window."""
from datetime import datetime
from typing import Any, Dict

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

from micro_cold_spray.core.components.ui.managers.ui_update_manager import (
    UIUpdateManager,
)
from micro_cold_spray.core.components.ui.tabs.dashboard_tab import DashboardTab
from micro_cold_spray.core.components.ui.widgets.base_widget import BaseWidget
from micro_cold_spray.core.components.ui.widgets.status.connection_status import (
    ConnectionStatus,
)
from micro_cold_spray.core.exceptions import UIError
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager


class SystemStateDisplay(BaseWidget):
    """Widget for displaying system state."""

    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        """Initialize with required dependencies."""
        super().__init__(
            widget_id="widget_system_state",
            ui_manager=ui_manager,
            update_tags=["system.state", "system.connection"],
            parent=parent
        )
        self.label = QLabel("System: STARTUP")
        self.label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.label.setFixedWidth(120)
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "system.state" in data:
                state = data.get("state", "DISCONNECTED")
                self.label.setText(f"System: {state}")

                # Add color coding for different states
                color = {
                    "CONNECTED": "#2ecc71",    # Green
                    "DISCONNECTED": "#e74c3c",  # Red
                    "STARTUP": "#f1c40f",      # Yellow
                    "ERROR": "#e74c3c"         # Red
                }.get(state, "#2c3e50")        # Default dark gray

                self.label.setStyleSheet(f"font-weight: bold; color: {color};")
                logger.debug(f"Updated system state display: {state}")

            elif "system.connection" in data:
                connected = data.get("connected", False)
                state = "CONNECTED" if connected else "DISCONNECTED"
                self.label.setText(f"System: {state}")
                color = "#2ecc71" if connected else "#e74c3c"
                self.label.setStyleSheet(f"font-weight: bold; color: {color};")
                logger.debug(f"Updated connection state: {state}")

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")


class SystemMessageDisplay(BaseWidget):
    """Widget for displaying system messages."""

    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        """Initialize with required dependencies."""
        super().__init__(
            widget_id="widget_system_message",
            ui_manager=ui_manager,
            update_tags=["system.message"],
            parent=parent
        )
        self.label = QLabel("System starting in disconnected mode")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "system.message" in data:
                message = data["system.message"]
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
            update_tags=["system.error"],
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
            if "system.error" in data:
                error = data["system.error"]
                self.label.setText(error)
                self.label.setStyleSheet("color: #e74c3c;")
        except Exception as e:
            logger.error(f"Error handling system error update: {e}")


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

            # Initialize only dashboard tab
            await self.dashboard_tab.initialize()

            # Subscribe to system messages
            await self._message_broker.subscribe(
                "system/state",
                self._handle_system_state
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
            main_layout.setContentsMargins(5, 5, 5, 5)
            central_widget.setLayout(main_layout)
            self.setCentralWidget(central_widget)

            # Create top strip
            top_strip = QFrame()
            top_strip.setFrameShape(QFrame.Shape.StyledPanel)
            top_strip.setFrameShadow(QFrame.Shadow.Raised)
            top_strip.setFixedHeight(40)
            top_layout = QHBoxLayout()
            top_layout.setContentsMargins(5, 2, 5, 2)
            top_strip.setLayout(top_layout)

            # Add system state display
            self.system_state = SystemStateDisplay(self._ui_manager)
            top_layout.addWidget(self.system_state)

            # Add message display
            message_frame = QFrame()
            message_frame.setFrameShape(QFrame.Shape.StyledPanel)
            message_frame.setFrameShadow(QFrame.Shadow.Sunken)
            message_layout = QVBoxLayout()
            message_layout.setContentsMargins(5, 2, 5, 2)
            message_layout.setSpacing(0)

            self.current_message = SystemMessageDisplay(self._ui_manager)
            self.current_message.setStyleSheet("""
                QLabel {
                    padding: 0;
                    margin: 0;
                    min-height: 20px;
                    qproperty-alignment: AlignCenter;
                }
            """)
            message_layout.addWidget(
                self.current_message,
                alignment=Qt.AlignmentFlag.AlignCenter
            )
            message_frame.setLayout(message_layout)
            top_layout.addWidget(message_frame, stretch=1)

            # Add connection status
            top_layout.addSpacing(5)
            self.connection_status = ConnectionStatus(self._ui_manager)
            self.connection_status.setFixedWidth(300)
            top_layout.addWidget(self.connection_status)

            # Add top strip to main layout
            main_layout.addWidget(top_strip)

            # Create and add only dashboard tab
            self.tab_widget = QTabWidget()
            self.dashboard_tab = DashboardTab(self._ui_manager)
            self.tab_widget.addTab(self.dashboard_tab, "Dashboard")

            main_layout.addWidget(self.tab_widget)

            # Create status bar
            self.status_bar = QStatusBar()
            self.status_bar.setMinimumHeight(30)
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    border-top: 1px solid #cccccc;
                    background-color: #f5f5f5;
                    padding: 4px 8px;
                    font-size: 12px;
                    min-height: 40px;
                    margin: 0;
                }
                QStatusBar::item {
                    border: none;
                    padding: 0;
                }
                QLabel {
                    padding: 4px 0;
                    margin: 0;
                }
            """)

            # Add error display to status bar
            self.error_label = SystemErrorDisplay(self._ui_manager)
            self.status_bar.addPermanentWidget(self.error_label, 1)
            self.setStatusBar(self.status_bar)

        except Exception as e:
            error_context = {
                "window": "MainWindow",
                "operation": "init_ui",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error initializing UI: {error_context}")
            raise UIError("UI initialization failed", error_context) from e

    async def _handle_system_state(self, data: Dict[str, Any]) -> None:
        """Handle system state updates."""
        try:
            state = data.get("state")
            if state:
                await self._ui_manager.send_update(
                    "system.state",
                    {"state": state}
                )
        except Exception as e:
            error_context = {
                "window": "MainWindow",
                "operation": "handle_system_state",
                "state": data.get("state"),
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error handling system state: {error_context}")
            raise UIError(
                "Failed to handle system state",
                error_context) from e

    async def cleanup(self) -> None:
        """Clean up all widgets and resources."""
        try:
            # Clean up only dashboard tab
            if hasattr(self, 'dashboard_tab'):
                await self.dashboard_tab.cleanup()

            # Clean up widgets
            if hasattr(self, 'system_state'):
                await self.system_state.cleanup()
            if hasattr(self, 'current_message'):
                await self.current_message.cleanup()
            if hasattr(self, 'error_label'):
                await self.error_label.cleanup()
            if hasattr(self, 'connection_status'):
                await self.connection_status.cleanup()

            self.is_closing = True
            logger.info("MainWindow cleanup complete")

        except Exception as e:
            error_context = {
                "window": "MainWindow",
                "operation": "cleanup",
                "timestamp": datetime.now().isoformat()
            }
            logger.exception("Error during MainWindow cleanup")
            raise UIError("MainWindow cleanup failed", error_context) from e

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        try:
            self.is_closing = True
            event.accept()
        except Exception:
            error_context = {
                "window": "MainWindow",
                "operation": "close",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error handling close event: {error_context}")
            event.ignore()
