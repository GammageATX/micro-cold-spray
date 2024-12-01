"""Diagnostics tab for system monitoring and control."""
from typing import Dict, Any, Optional
import logging
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSplitter
)
from PySide6.QtCore import Qt

from ..widgets.base_widget import BaseWidget
from ..managers.ui_update_manager import UIUpdateManager
from ..widgets.diagnostics.control_panel import ControlPanel
from ..widgets.diagnostics.tag_monitor import TagMonitor
from ..widgets.diagnostics.validation_panel import ValidationPanel

logger = logging.getLogger(__name__)


class DiagnosticsTab(BaseWidget):
    """Tab for system diagnostics and monitoring."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="tab_diagnostics",
            ui_manager=ui_manager,
            update_tags=[
                "system.state",
                "system.message",
                "hardware.status"
            ],
            parent=parent
        )

        # Store widget references
        self._control_panel: Optional[ControlPanel] = None
        self._tag_monitor: Optional[TagMonitor] = None
        self._validation_panel: Optional[ValidationPanel] = None

        self._init_ui()
        logger.info("Diagnostics tab initialized")

    def _init_ui(self) -> None:
        """Initialize the diagnostics tab UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Add header
        header = QLabel("System Diagnostics")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)

        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Control Panel
        left_frame = QFrame()
        left_layout = QVBoxLayout()
        left_frame.setLayout(left_layout)

        self._control_panel = ControlPanel(self._ui_manager)
        left_layout.addWidget(self._control_panel)

        splitter.addWidget(left_frame)

        # Right side - Monitoring
        right_frame = QFrame()
        right_layout = QVBoxLayout()
        right_frame.setLayout(right_layout)

        # Tag Monitor
        self._tag_monitor = TagMonitor(self._ui_manager)
        right_layout.addWidget(self._tag_monitor)

        # Validation Panel
        self._validation_panel = ValidationPanel(self._ui_manager)
        right_layout.addWidget(self._validation_panel)

        splitter.addWidget(right_frame)

        # Set initial splitter sizes (40/60 split)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter)
        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates from UIUpdateManager."""
        try:
            if "system.state" in data:
                state = data["system.state"]
                logger.debug(
                    f"Diagnostics received system state update: {state}")
                # Update tab state if needed

            elif "system.message" in data:
                message = data["system.message"]
                logger.debug(f"Diagnostics received system message: {message}")
                # Update tab message if needed

            elif "hardware.status" in data:
                status = data["hardware.status"]
                logger.debug(f"Diagnostics received hardware status: {status}")
                # Update hardware status if needed

        except Exception as e:
            logger.error(f"Error handling UI update in DiagnosticsTab: {e}")
            await self.send_update("system.error", f"Diagnostics error: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up diagnostics tab and child widgets."""
        try:
            # Clean up child widgets first
            if self._control_panel is not None:
                try:
                    await self._control_panel.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up control panel: {e}")

            if self._tag_monitor is not None:
                try:
                    await self._tag_monitor.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up tag monitor: {e}")

            if self._validation_panel is not None:
                try:
                    await self._validation_panel.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up validation panel: {e}")

            # Then clean up self
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during diagnostics tab cleanup: {e}")
