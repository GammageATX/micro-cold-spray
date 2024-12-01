"""Widget for displaying sequence execution progress."""
import logging
from datetime import datetime
from typing import Any, Dict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


class ProgressDisplay(BaseWidget):
    """Displays sequence execution progress."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="display_dashboard_progress",
            ui_manager=ui_manager,
            update_tags=[
                "sequence.loaded",
                "sequence.started",
                "sequence.step.started",
                "sequence.step.completed",
                "sequence.completed",
                "sequence.error"
            ],
            parent=parent
        )

        # Track execution state
        self._sequence_start = None
        self._current_step = None
        self._step_count = 0
        self._completed_steps = 0

        self._init_ui()
        self._start_timer()
        logger.info("Progress display initialized")

    def _init_ui(self):
        """Initialize progress display UI."""
        layout = QVBoxLayout()

        # Current step info
        step_layout = QHBoxLayout()
        self.step_label = QLabel("Current Step:")
        self.step_name = QLabel("No sequence running")
        self.step_name.setStyleSheet("font-weight: bold;")
        step_layout.addWidget(self.step_label)
        step_layout.addWidget(self.step_name)
        layout.addLayout(step_layout)

        # Step details
        self.step_details = QLabel("")
        self.step_details.setWordWrap(True)
        layout.addWidget(self.step_details)

        # Progress bar
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout)

        # Step counter
        counter_layout = QHBoxLayout()
        self.step_counter = QLabel("Steps: 0/0")
        self.execution_time = QLabel("Time: 00:00:00")
        counter_layout.addWidget(self.step_counter)
        counter_layout.addWidget(self.execution_time)
        layout.addLayout(counter_layout)

        # Status line with proper Qt constants
        self.status_line = QLabel("")
        self.status_line.setFrameShape(QFrame.Shape.Panel)
        self.status_line.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_line)

        self.setLayout(layout)

    def _start_timer(self) -> None:
        """Start execution time update timer."""
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_execution_time)
        self._timer.start(1000)  # Update every second

    def _update_execution_time(self) -> None:
        """Update execution time display."""
        if self._sequence_start:
            elapsed = datetime.now() - self._sequence_start
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            seconds = int(elapsed.total_seconds() % 60)
            self.execution_time.setText(
                f"Time: {
                    hours:02d}:{
                    minutes:02d}:{
                    seconds:02d}")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "sequence.step.started" in data:
                await self._handle_step_start(data["sequence.step.started"])
            elif "sequence.step.completed" in data:
                await self._handle_step_complete(data["sequence.step.completed"])
            elif "sequence.completed" in data:
                await self._handle_sequence_complete(data["sequence.completed"])
            elif "sequence.error" in data:
                await self._handle_sequence_complete({
                    "success": False,
                    "message": data["sequence.error"]
                })
        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self.send_update("system.error", f"Progress display error: {str(e)}")

    async def _handle_step_start(self, step: Dict[str, Any]) -> None:
        """Handle step start."""
        try:
            # Update display
            self.step_name.setText(step.get("name", "Unknown Step"))
            self.step_details.setText(
                f"Action: {step.get('action', 'Unknown')}\n"
                f"Parameters: {step.get('parameters', {})}"
            )

            # Start timing if first step
            if not self._sequence_start:
                self._sequence_start = datetime.now()
                self._step_count = step.get("total_steps", 0)

            self._current_step = step
            self.status_line.setText("Step in progress...")
            self.status_line.setStyleSheet("color: blue;")

        except Exception as e:
            logger.error(f"Error handling step start: {e}")
            await self.send_update("system.error", f"Error handling step start: {str(e)}")

    async def _handle_step_complete(self, result: Dict[str, Any]) -> None:
        """Handle step completion."""
        try:
            self._completed_steps += 1

            # Update progress
            progress = (self._completed_steps / self._step_count) * 100
            self.progress_bar.setValue(int(progress))

            # Update step counter
            self.step_counter.setText(
                f"Steps: {self._completed_steps}/{self._step_count}")

            if result.get("success", False):
                self.status_line.setText("Step completed successfully")
                self.status_line.setStyleSheet("color: green;")
            else:
                self.status_line.setText(
                    f"Step failed: {
                        result.get(
                            'message',
                            'Unknown error')}")
                self.status_line.setStyleSheet("color: red;")

        except Exception as e:
            logger.error(f"Error handling step complete: {e}")

    async def _handle_sequence_complete(self, result: Dict[str, Any]) -> None:
        """Handle sequence completion."""
        try:
            if result.get("success", False):
                self.status_line.setText("Sequence completed successfully")
                self.status_line.setStyleSheet("color: green;")
            else:
                self.status_line.setText(
                    f"Sequence failed: {
                        result.get(
                            'message',
                            'Unknown error')}")
                self.status_line.setStyleSheet("color: red;")

            # Reset sequence state
            self._sequence_start = None
            self._current_step = None

        except Exception as e:
            logger.error(f"Error handling sequence complete: {e}")

    def reset_display(self) -> None:
        """Reset progress display."""
        self.step_name.setText("No sequence running")
        self.step_details.setText("")
        self.progress_bar.setValue(0)
        self.step_counter.setText("Steps: 0/0")
        self.execution_time.setText("Time: 00:00:00")
        self.status_line.setText("")
        self._sequence_start = None
        self._current_step = None
        self._completed_steps = 0
        self._current_step = None
        self._completed_steps = 0
