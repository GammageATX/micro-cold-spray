"""Configuration status widget."""
import logging
from typing import Any, Dict

from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


class ConfigStatus(BaseWidget):
    """Widget for displaying configuration status."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_config_status",
            ui_manager=ui_manager,
            update_tags=[
                "config.status",
                "config.validation"
            ],
            parent=parent
        )

        self._init_ui()
        logger.info("Config status widget initialized")

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout()

        # Status label
        self.status_label = QLabel("Configuration Status: Ready")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "config.status" in data:
                status = data["config.status"]
                self._update_status(status)

            if "config.validation" in data:
                validation = data["config.validation"]
                self._handle_validation(validation)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    def _update_status(self, status: Dict[str, Any]) -> None:
        """Update status display."""
        try:
            state = status.get("state", "ready")
            progress = status.get("progress")

            # Update status label
            self.status_label.setText(f"Configuration Status: {state.title()}")

            # Update progress bar
            if progress is not None:
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(int(progress * 100))
            else:
                self.progress_bar.setVisible(False)

        except Exception as e:
            logger.error(f"Error updating status: {e}")

    def _handle_validation(self, validation: Dict[str, Any]) -> None:
        """Handle validation results."""
        try:
            if validation.get("valid", True):
                self.status_label.setStyleSheet("color: green;")
            else:
                self.status_label.setStyleSheet("color: red;")
                errors = validation.get("errors", [])
                if errors:
                    self.status_label.setText(
                        f"Configuration Error: {errors[0]}"
                    )

        except Exception as e:
            logger.error(f"Error handling validation: {e}")
