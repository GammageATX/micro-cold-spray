"""Sequence control widget for loading and controlling sequences."""
import asyncio
from typing import Any, Dict, Protocol, runtime_checkable

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from micro_cold_spray.core.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.ui.widgets.base_widget import BaseWidget
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker


@runtime_checkable
class MainWindowProtocol(Protocol):
    """Protocol for main window interface."""
    @property
    def connection_status(self) -> Any:
        """Get connection status widget."""
        ...


class CustomProgressBar(QProgressBar):
    """Custom progress bar with centered text regardless of value."""

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setTextVisible(True)
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: #2c3e50;
                color: white;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
            }
        """)


class SequenceControl(BaseWidget):
    """Widget for sequence loading and control."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        message_broker: MessageBroker,
        parent=None
    ):
        super().__init__(
            widget_id="control_dashboard_sequence",
            ui_manager=ui_manager,
            update_tags=[
                "data/files",
                "sequence/state",
                "sequence/progress",
                "sequence/error",
                "system/state",
                "system/connection",
                "system/message",
                "system/error"
            ],
            parent=parent
        )

        # Store dependencies
        self._message_broker = message_broker

        self._sequences = {}
        self._system_state = "STARTUP"
        self._connection_state = {"connected": False}
        self._load_task = None

        self._init_ui()
        logger.info("Sequence control initialized")

    async def initialize(self) -> None:
        """Async initialization."""
        try:
            # First wait for base initialization to complete
            await super().initialize()
            logger.info("Base initialization complete, loading sequence library")

            # Now load the sequence library
            self._load_task = asyncio.create_task(self._load_sequence_library())
            self._load_task.add_done_callback(self._on_load_complete)

        except Exception as e:
            logger.error(f"Error during sequence control initialization: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _load_sequence_library(self) -> None:
        """Load available sequences."""
        try:
            await self._ui_manager.send_update(
                "sequence/request",
                {
                    "action": "list"
                }
            )
        except Exception as e:
            logger.error(f"Error requesting sequence list: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "data/files" in data:
                file_data = data["data/files"]
                if file_data.get("type") == "sequences":
                    self.sequence_combo.clear()
                    self.sequence_combo.addItem("")  # Blank default option

                    if "files" in file_data:
                        for sequence in file_data["files"]:
                            if isinstance(sequence, str):
                                self.sequence_combo.addItem(sequence)
                                self._sequences[sequence] = {"name": sequence}
                        logger.debug(f"Updated sequence list with {len(self._sequences)} sequences")

            elif "sequence/state" in data:
                state = data["sequence/state"]
                await self._handle_sequence_state(state)

            elif "sequence/progress" in data:
                progress = data["sequence/progress"]
                await self._handle_sequence_progress(progress)

            elif "sequence/error" in data:
                error = data["sequence/error"]
                await self._handle_sequence_error(error)

            elif "system/state" in data:
                self._system_state = data["system/state"]
                await self._update_button_states()

            elif "system/connection" in data:
                self._connection_state = data
                await self._update_button_states()

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _handle_sequence_state(self, state: Dict[str, Any]) -> None:
        """Handle sequence state updates."""
        try:
            status = state.get("state", "")
            if status == "RUNNING":
                self.start_button.setEnabled(False)
                self.cancel_button.setEnabled(True)
                self.status_label.setText("Status: Running")
                self.status_label.setStyleSheet("color: #27ae60;")
            elif status == "COMPLETED":
                self.start_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
                self.status_label.setText("Status: Completed")
                self.status_label.setStyleSheet("color: #2980b9;")
            elif status == "CANCELLED":
                self.start_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
                self.status_label.setText("Status: Cancelled")
                self.status_label.setStyleSheet("color: #e67e22;")
            elif status == "ERROR":
                self.start_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
                self.status_label.setText("Status: Error")
                self.status_label.setStyleSheet("color: #e74c3c;")

        except Exception as e:
            logger.error(f"Error handling sequence state: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _handle_sequence_progress(self, progress: Dict[str, Any]) -> None:
        """Handle sequence progress updates."""
        try:
            percent = progress.get("percent", 0)
            step = progress.get("step", "")
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"{step} ({percent}%)")

        except Exception as e:
            logger.error(f"Error handling sequence progress: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _handle_sequence_error(self, error: Dict[str, Any]) -> None:
        """Handle sequence error updates."""
        try:
            message = error.get("message", "Unknown error")
            self.status_label.setText(f"Error: {message}")
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)

        except Exception as e:
            logger.error(f"Error handling sequence error: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _update_button_states(self) -> None:
        """Update button states based on system state and connection."""
        try:
            connected = self._connection_state.get("connected", False)
            sequence_selected = bool(self.sequence_combo.currentText())

            self.load_button.setEnabled(connected and sequence_selected)
            self.start_button.setEnabled(
                connected and
                sequence_selected and
                self._system_state not in ["ERROR", "STARTUP"]
            )

        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _init_ui(self) -> None:
        """Initialize the sequence control UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Create frame
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        frame_layout = QVBoxLayout()

        # Add title
        title = QLabel("Sequence Control")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        frame_layout.addWidget(title)

        # Sequence Selection
        select_layout = QHBoxLayout()
        select_label = QLabel("Sequence:")
        self.sequence_combo = QComboBox()
        self.sequence_combo.setMinimumWidth(200)
        self.sequence_combo.addItem("")  # Blank default option
        self.load_button = QPushButton("Load")
        select_layout.addWidget(select_label)
        select_layout.addWidget(self.sequence_combo)
        select_layout.addWidget(self.load_button)
        frame_layout.addLayout(select_layout)

        # Status Display
        self.status_label = QLabel("Status: No Sequence Selected")
        self.status_label.setStyleSheet("color: gray; margin-top: 5px;")
        frame_layout.addWidget(self.status_label)

        # Progress Bar
        self.progress_bar = CustomProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ready")
        frame_layout.addWidget(self.progress_bar)

        # Control Buttons
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Sequence")
        self.cancel_button = QPushButton("Cancel")

        # Initially disable control buttons
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

        # Add buttons to layout
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)

        frame_layout.addLayout(button_layout)

        # Set frame layout
        frame.setLayout(frame_layout)
        layout.addWidget(frame)

        # Add stretch to keep widget compact
        layout.addStretch()

        self.setLayout(layout)

        # Connect signals with async handlers
        self.load_button.clicked.connect(
            lambda: asyncio.create_task(self._on_load_clicked())
        )
        self.start_button.clicked.connect(
            lambda: asyncio.create_task(self._on_start_clicked())
        )
        self.cancel_button.clicked.connect(
            lambda: asyncio.create_task(self._on_cancel_clicked())
        )
        self.sequence_combo.currentTextChanged.connect(
            self._on_sequence_selected)

    async def _on_load_clicked(self) -> None:
        """Handle load button click."""
        try:
            sequence_name = self.sequence_combo.currentText()
            if sequence_name:
                await self._ui_manager.send_update(
                    "sequence/request",
                    {
                        "action": "load",
                        "name": sequence_name
                    }
                )
        except Exception as e:
            logger.error(f"Error loading sequence: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _on_start_clicked(self) -> None:
        """Handle start button click."""
        try:
            await self._ui_manager.send_update(
                "sequence/control",
                {
                    "action": "start"
                }
            )
        except Exception as e:
            logger.error(f"Error starting sequence: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        try:
            await self._ui_manager.send_update(
                "sequence/control",
                {
                    "action": "stop"
                }
            )
        except Exception as e:
            logger.error(f"Error canceling sequence: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            )

    def update_progress(self, value: int) -> None:
        """Update progress bar value."""
        try:
            self.progress_bar.setValue(value)
            if value >= 100:
                self.progress_bar.setFormat("Complete")
            else:
                self.progress_bar.setFormat(f"{value}%")
        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def _on_sequence_selected(self, sequence_name: str) -> None:
        """Handle sequence selection change."""
        try:
            # Enable/disable buttons based on selection
            has_selection = bool(sequence_name)
            self.load_button.setEnabled(has_selection)
            self.start_button.setEnabled(False)  # Only enable after loading
            self.cancel_button.setEnabled(False)

            # Update status
            if has_selection:
                self.status_label.setText(f"Status: {sequence_name} selected")
            else:
                self.status_label.setText("Status: No sequence selected")

        except Exception as e:
            logger.error(f"Error handling sequence selection: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            ))

    def _on_load_complete(self, task) -> None:
        """Handle sequence library load completion."""
        try:
            task.result()  # This will raise any exceptions that occurred
        except Exception as e:
            logger.error(f"Sequence library load task failed: {e}")
            logger.error(f"Load task error details:\n{task.exception()}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_control",
                    "message": str(e),
                    "level": "error"
                }
            ))
