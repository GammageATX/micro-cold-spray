"""Sequence progress display widget."""
import logging
from typing import Any, Dict, Optional
import asyncio

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar
)

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


class ProgressDisplay(BaseWidget):
    """Widget for displaying sequence progress."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_sequence_progress",
            ui_manager=ui_manager,
            update_tags=[
                "sequence/progress",
                "sequence/step",
                "sequence/state",
                "system/connection",
                "system/error"
            ],
            parent=parent
        )

        self._current_step: Optional[str] = None
        self._progress: float = 0.0
        self._state: str = "idle"
        self._init_ui()
        logger.info("Progress display initialized")

    def _init_ui(self) -> None:
        """Initialize the progress display UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Status label
        self._status_label = QLabel("No sequence running")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        # Step info
        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("Current Step:"))
        self._step_label = QLabel("None")
        step_layout.addWidget(self._step_label, 1)
        layout.addLayout(step_layout)

        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "sequence/progress" in data:
                progress = data["sequence/progress"]
                if isinstance(progress, (int, float)):
                    self._progress = float(progress)
                    self._update_display()

            elif "sequence/step" in data:
                step = data["sequence/step"]
                if isinstance(step, str):
                    self._current_step = step
                    self._update_display()

            elif "sequence/state" in data:
                state = data["sequence/state"]
                if isinstance(state, str):
                    self._state = state
                    self._update_display()

            elif "system/connection" in data:
                connected = data.get("connected", False)
                if not connected:
                    self._reset_display()

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "progress_display",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _update_display(self) -> None:
        """Update the display with current progress."""
        try:
            # Update progress bar
            self._progress_bar.setValue(int(self._progress * 100))

            # Update status label
            if self._state == "running":
                self._status_label.setText(f"Sequence Running ({int(self._progress * 100)}%)")
            elif self._state == "paused":
                self._status_label.setText("Sequence Paused")
            elif self._state == "completed":
                self._status_label.setText("Sequence Completed")
            elif self._state == "error":
                self._status_label.setText("Sequence Error")
            else:
                self._status_label.setText("No Sequence Running")

            # Update step label
            if self._current_step:
                self._step_label.setText(self._current_step)
            else:
                self._step_label.setText("None")

        except Exception as e:
            logger.error(f"Error updating display: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "progress_display",
                    "message": str(e),
                    "level": "error"
                }
            ))

    def _reset_display(self) -> None:
        """Reset display to initial state."""
        try:
            self._progress = 0.0
            self._current_step = None
            self._state = "idle"
            self._update_display()
        except Exception as e:
            logger.error(f"Error resetting display: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "progress_display",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during progress display cleanup: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "progress_display",
                    "message": str(e),
                    "level": "error"
                }
            )
