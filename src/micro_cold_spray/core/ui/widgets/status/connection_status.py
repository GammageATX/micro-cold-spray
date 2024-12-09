"""Connection status and user selection widget."""
import logging
import asyncio
from typing import Any, Dict, List

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QInputDialog

from micro_cold_spray.core.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.ui.widgets.base_widget import BaseWidget
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class StatusIndicator(QFrame):
    """A colored square indicator for connection status."""

    def __init__(self, size: int = 6):
        super().__init__()
        self._indicator_size = size
        self.setFixedSize(size, size)
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setConnected(False)

    def setConnected(self, connected: bool) -> None:
        """Set the connection status color."""
        color = QColor("#2ecc71") if connected else QColor("#e74c3c")
        self.setStyleSheet(f"""
            background-color: {color.name()};
            border: 1px solid #2c3e50;
            border-radius: {self._indicator_size // 4}px;
        """)


class ConnectionStatus(BaseWidget):
    """Widget showing connection status and user selection."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_system_connection",
            ui_manager=ui_manager,
            update_tags=[
                "hardware/status",
                "system/connection",
                "config/update",
                "system/error"
            ],
            parent=parent
        )
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._init_ui()
        logger.info("Connection status widget initialized")

        # Load initial state
        asyncio.create_task(self._load_initial_state())

    async def _load_initial_state(self) -> None:
        """Load initial state from config."""
        try:
            # Get initial config directly
            config = await self._config_manager.get_config("application")
            env_config = config.get("application", {}).get("environment", {})

            # Set initial user list
            users = env_config.get("user_history", [])
            if users:
                self.set_users(users)

            # Set current user if one is saved
            current_user = env_config.get("user", "")
            if current_user:
                self.user_combo.setCurrentText(current_user)

            # Subscribe to config updates for real-time changes
            await self._message_broker.subscribe(
                "config/update",
                self._handle_config_update
            )

        except Exception as e:
            logger.error(f"Error loading initial state: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "connection_status",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _handle_config_update(self, data: Dict[str, Any]) -> None:
        """Handle real-time config updates."""
        try:
            if "application" in data.get("data", {}):
                env_config = data["data"]["application"].get("environment", {})
                users = env_config.get("user_history", [])
                if users:
                    self.set_users(users)

                # Update current user if changed
                current_user = env_config.get("user", "")
                if current_user:
                    self.user_combo.setCurrentText(current_user)

        except Exception as e:
            logger.error(f"Error handling config update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "connection_status",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "hardware/status" in data:
                status = data["hardware/status"]
                self.update_plc_status(status.get("plc_connected", False))
                self.update_ssh_status(status.get("ssh_connected", False))

            elif "system/connection" in data:
                connected = data.get("connected", False)
                self.update_plc_status(connected)
                self.update_ssh_status(connected)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "connection_status",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _init_ui(self) -> None:
        """Initialize the connection status UI."""
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(10)

        # Create ultra-compact indicator group
        indicators_frame = QFrame()
        indicators_layout = QHBoxLayout()
        indicators_layout.setContentsMargins(0, 0, 0, 0)
        indicators_layout.setSpacing(1)

        # PLC Status - More compact
        plc_layout = QHBoxLayout()
        plc_layout.setSpacing(1)
        self.plc_indicator = StatusIndicator()
        plc_label = QLabel("PLC")
        plc_label.setFixedWidth(20)
        plc_label.setStyleSheet("font-size: 8pt;")
        plc_layout.addWidget(self.plc_indicator)
        plc_layout.addWidget(plc_label)
        indicators_layout.addLayout(plc_layout)

        # Small spacer between indicators
        indicators_layout.addSpacing(2)

        # SSH Status - More compact
        ssh_layout = QHBoxLayout()
        ssh_layout.setSpacing(1)
        self.ssh_indicator = StatusIndicator()
        ssh_label = QLabel("SSH")
        ssh_label.setFixedWidth(20)
        ssh_label.setStyleSheet("font-size: 8pt;")
        ssh_layout.addWidget(self.ssh_indicator)
        ssh_layout.addWidget(ssh_label)
        indicators_layout.addLayout(ssh_layout)

        indicators_frame.setLayout(indicators_layout)
        indicators_frame.setFixedWidth(90)
        layout.addWidget(indicators_frame)

        # User Selection
        user_label = QLabel("User:")
        user_label.setFixedWidth(35)

        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(150)
        self.user_combo.setMaximumWidth(150)
        self.user_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.user_combo.addItems(["Default User", "Add User..."])
        self.user_combo.currentTextChanged.connect(
            lambda text: asyncio.create_task(self._on_user_selected(text)))

        layout.addWidget(user_label)
        layout.addWidget(self.user_combo)

        self.setLayout(layout)

    async def _on_user_selected(self, text: str) -> None:
        """Handle user selection changed."""
        try:
            if text == "Add User...":
                # Show dialog to add new user
                new_user, ok = QInputDialog.getText(
                    self,
                    "Add New User",
                    "Enter new user name:"
                )

                if ok and new_user:
                    # Add to combo box immediately for responsiveness
                    current_items = [
                        self.user_combo.itemText(i)
                        for i in range(self.user_combo.count() - 1)  # Exclude "Add User..."
                    ]
                    if new_user not in current_items:
                        # Insert new user before "Add User..." entry
                        self.user_combo.insertItem(self.user_combo.count() - 1, new_user)
                        self.user_combo.setCurrentText(new_user)

                        # Update application config directly
                        await self._config_manager.update_config("application", {
                            "application": {
                                "environment": {
                                    "user": new_user,
                                    "user_history": current_items + [new_user]
                                }
                            }
                        })

                        logger.info(f"Added new user: {new_user}")
                    else:
                        logger.warning(f"User {new_user} already exists")
                        # Restore previous selection
                        self.user_combo.setCurrentText(current_items[0])
                else:
                    # If cancelled or empty, restore previous selection
                    self.user_combo.setCurrentText("Default User")

        except Exception as e:
            logger.error(f"Error handling user selection: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "connection_status",
                    "message": str(e),
                    "level": "error"
                }
            )
            # Restore to default user on error
            self.user_combo.setCurrentText("Default User")

    def update_plc_status(self, connected: bool) -> None:
        """Update PLC connection status."""
        self.plc_indicator.setConnected(connected)
        logger.debug(f"Updated PLC status indicator: {connected}")

    def update_ssh_status(self, connected: bool) -> None:
        """Update SSH connection status."""
        self.ssh_indicator.setConnected(connected)
        logger.debug(f"Updated SSH status indicator: {connected}")

    def set_users(self, users: List[str]) -> None:
        """Update the list of available users."""
        current = self.user_combo.currentText()
        if current == "Add User...":
            current = "Default User"

        self.user_combo.clear()

        # Ensure we always have Default User as first option
        if "Default User" not in users:
            users = ["Default User"] + users

        # Add all users plus the "Add User..." option at the end
        self.user_combo.addItems(users + ["Add User..."])

        # Try to restore the previous selection
        index = self.user_combo.findText(current)
        if index >= 0:
            self.user_combo.setCurrentIndex(index)
        else:
            # Default to first user if previous selection not found
            self.user_combo.setCurrentIndex(0)
