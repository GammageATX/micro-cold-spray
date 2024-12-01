"""Connection status and user selection widget."""
import logging
from typing import Any, Dict, List

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

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

    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        super().__init__(
            widget_id="widget_system_connection",
            ui_manager=ui_manager,
            update_tags=["hardware_status", "system.connection"],
            parent=parent
        )
        self._init_ui()
        logger.info("Connection status widget initialized")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "hardware_status" in data:
                status = data["hardware_status"]
                self.update_plc_status(status.get("plc_connected", False))
                self.update_ssh_status(status.get("ssh_connected", False))

            elif "system.connection" in data:
                connected = data.get("connected", False)
                self.update_plc_status(connected)
                self.update_ssh_status(connected)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

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
        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(200)
        self.user_combo.setMaximumWidth(200)
        self.user_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.user_combo.addItems(["Default User"])
        layout.addWidget(self.user_combo)

        self.setLayout(layout)

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
        self.user_combo.clear()
        self.user_combo.addItems(users)

        # Try to restore the previous selection
        index = self.user_combo.findText(current)
        if index >= 0:
            self.user_combo.setCurrentIndex(index)
