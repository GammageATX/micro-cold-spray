"""Sequence control widget for loading and controlling sequences."""
import asyncio
import time
from pathlib import Path
from typing import Any, Dict, Protocol, runtime_checkable

import yaml
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
from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget


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
        parent=None
    ):
        super().__init__(
            widget_id="control_dashboard_sequence",
            ui_manager=ui_manager,
            update_tags=[
                "sequence.state",
                "sequence.progress",
                "sequence.error",
                "system.state",
                "system.connection",
                "system.message"
            ],
            parent=parent
        )

        self._sequences = {}
        self._system_state = "STARTUP"
        self._connection_state = {"connected": False}

        self._init_ui()
        self._load_sequence_library()
        logger.info("Sequence control initialized")

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

    def _load_sequence_library(self):
        """Load available sequences from the library directory."""
        try:
            library_path = Path("data/sequences/library")
            logger.debug(f"Loading sequences from {library_path}")

            if not library_path.exists():
                logger.warning(f"Sequence library path not found: {library_path}")
                return

            # Load all yaml files from the library
            for sequence_file in library_path.glob("*.yaml"):
                try:
                    logger.debug(f"Loading sequence file: {sequence_file}")
                    with open(sequence_file, 'r') as f:
                        sequence_data = yaml.safe_load(f)

                    # Extract sequence name from metadata
                    if sequence_data and 'sequence' in sequence_data:
                        metadata = sequence_data['sequence'].get('metadata', {})
                        name = metadata.get('name')
                        if name:
                            self._sequences[name] = sequence_data
                            self.sequence_combo.addItem(name)
                            logger.debug(f"Added sequence '{name}' to combo box")
                        else:
                            logger.warning(f"No name found in sequence metadata: {metadata}")
                    else:
                        logger.warning(f"Invalid sequence format in {sequence_file}")

                except Exception as e:
                    logger.error(f"Error loading sequence file {sequence_file}: {str(e)}")

            logger.debug(f"Loaded {len(self._sequences)} sequences")

        except Exception as e:
            logger.error(f"Error loading sequence library: {str(e)}")

    def _on_sequence_selected(self, sequence_name: str) -> None:
        """Handle sequence selection change."""
        try:
            if not sequence_name:
                self.start_button.setEnabled(False)
                self.cancel_button.setEnabled(False)
                self.status_label.setText("Status: No Sequence Selected")
                self.status_label.setStyleSheet("color: gray;")
                return

            self.status_label.setText(f"Selected: {sequence_name}")
            self.status_label.setStyleSheet("")

        except Exception as e:
            logger.error(f"Error handling sequence selection: {e}")

    async def _on_load_clicked(self) -> None:
        """Handle load button click."""
        try:
            selected = self.sequence_combo.currentText()
            logger.debug(f"Load clicked for sequence: {selected}")

            if not selected:
                self.start_button.setEnabled(False)
                self.cancel_button.setEnabled(False)
                self.progress_bar.setValue(0)
                self.status_label.setText("Status: No Sequence Selected")
                self.status_label.setStyleSheet("color: gray;")
                return

            if selected in self._sequences:
                sequence_data = self._sequences[selected]
                logger.debug(f"Loading sequence data: {sequence_data}")

                self.start_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
                self.status_label.setText(f"Loaded: {selected}")
                self.status_label.setStyleSheet("")
                self.progress_bar.setValue(0)
                self.progress_bar.setFormat("Ready")

                # Get user from parent window's connection status
                parent_window = self.window()
                user = "Default User"

                if isinstance(parent_window, MainWindowProtocol):
                    user = parent_window.connection_status.user_combo.currentText()
                else:
                    logger.warning("Could not find main window, using default user")

                # Create sequence loaded data
                sequence_loaded_data = {
                    "name": selected,
                    "user": user,
                    "metadata": sequence_data.get("sequence", {}).get("metadata", {}),
                    "timestamp": time.time()
                }

                # Add debug logging
                logger.debug(f"Sending sequence.loaded update: {sequence_loaded_data}")

                # First publish to message broker
                await self._ui_manager._message_broker.publish(
                    "sequence/loaded",
                    sequence_loaded_data
                )

                # Then send through UIUpdateManager for UI updates
                await self.send_update(
                    "sequence.loaded",
                    sequence_loaded_data
                )

        except Exception as e:
            logger.error(f"Error loading sequence: {e}")
            await self.send_update("system.error", f"Error loading sequence: {str(e)}")

    async def _on_start_clicked(self) -> None:
        """Handle start button click."""
        try:
            # Check system state and connection first
            if not self._connection_state.get("connected", False):
                self.status_label.setText("Cannot start: System disconnected")
                self.status_label.setStyleSheet("color: red;")
                await self.send_update(
                    "system.message",
                    "Cannot start sequence in disconnected state"
                )
                return

            if self._system_state not in ["READY", "IDLE"]:
                self.status_label.setText(f"Cannot start: System {self._system_state}")
                self.status_label.setStyleSheet("color: red;")
                return

            selected = self.sequence_combo.currentText()
            if not selected:
                return

            # If all checks pass, update UI and send start command
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.status_label.setText("Status: Running")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Starting...")

            await self.send_update(
                "sequence.state",
                {
                    "state": "STARTING",
                    "timestamp": time.time()
                }
            )

        except Exception as e:
            logger.error(f"Error starting sequence: {e}")
            await self.send_update("system.error", f"Error starting sequence: {str(e)}")

    async def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        try:
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Status: Cancelled")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Cancelled")

            await self.send_update(
                "sequence.state",
                {
                    "state": "CANCELLED",
                    "timestamp": time.time()
                }
            )

        except Exception as e:
            logger.error(f"Error cancelling sequence: {e}")
            await self.send_update("system.error", f"Error cancelling sequence: {str(e)}")

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

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle updates from UIUpdateManager."""
        try:
            if "system.state" in data:
                old_state = self._system_state
                self._system_state = data["system.state"]
                logger.debug(
                    f"System state changed: {old_state} -> {self._system_state}")
                await self._update_button_states()

            elif "system.connection" in data:
                old_connected = self._connection_state.get("connected", False)
                self._connection_state = data["system.connection"]
                logger.debug(
                    f"Connection state changed: {old_connected} -> {
                        self._connection_state.get('connected')}")
                await self._update_button_states()

            elif "sequence.state" in data:
                sequence_state = data["sequence.state"]
                self._handle_sequence_state(sequence_state)
                logger.debug(f"Sequence state update: {sequence_state}")

            elif "sequence.progress" in data:
                progress = data["sequence.progress"]
                self.update_progress(progress)
                logger.debug(f"Progress update: {progress}")

            elif "sequence.error" in data:
                error = data["sequence.error"]
                self.status_label.setText(f"Error: {error}")
                self.status_label.setStyleSheet("color: red;")
                logger.error(f"Sequence error: {error}")

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self.send_update("system.error", f"Sequence control error: {str(e)}")

    def _handle_sequence_state(self, state: Dict[str, Any]) -> None:
        """Handle sequence state updates."""
        try:
            state_value = state.get("state", "")
            if state_value == "RUNNING":
                self.start_button.setEnabled(False)
                self.cancel_button.setEnabled(True)
                self.status_label.setText("Status: Running")
                self.progress_bar.setFormat("Running...")
            elif state_value == "COMPLETED":
                self.start_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
                self.status_label.setText("Status: Complete")
                self.progress_bar.setFormat("Complete")
            elif state_value == "CANCELLED":
                self.start_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
                self.status_label.setText("Status: Cancelled")
                self.progress_bar.setFormat("Cancelled")
            elif state_value == "ERROR":
                self.start_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
                self.status_label.setText("Status: Error")
                self.progress_bar.setFormat("Error")

        except Exception as e:
            logger.error(f"Error handling sequence state: {e}")

    async def _update_button_states(self) -> None:
        """Update button states based on system state."""
        try:
            can_start = self._connection_state.get("connected", False)
            system_ready = self._system_state in ["READY", "IDLE"]

            if not can_start:
                await self.send_update(
                    "system.message",
                    "System disconnected"
                )
            elif not system_ready:
                await self.send_update(
                    "system.message",
                    f"System in {self._system_state} state"
                )
            else:
                self.status_label.setText("Status: Ready to start")

            logger.debug(
                "Button states updated - "
                f"Start: {can_start}, "
                f"Cancel: {self._system_state == 'RUNNING'}"
            )

        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            await self.send_update("system.error", f"Error updating controls: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clean up any resources
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
