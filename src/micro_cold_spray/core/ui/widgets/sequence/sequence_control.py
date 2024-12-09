"""Sequence control widget for loading and controlling sequences."""
import asyncio
from typing import Any, Dict, Protocol, runtime_checkable
from datetime import datetime

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
            widget_id="widget_control_sequence",
            ui_manager=ui_manager,
            update_tags=["error"],
            parent=parent
        )

        # Store dependencies
        self._message_broker = message_broker
        self._sequences = {}
        self._system_state = "STARTUP"
        self._connection_state = {"connected": False}
        self._pending_requests = {}  # Track pending requests by ID

        self._init_ui()
        logger.info("Sequence control initialized")

        # Subscribe to response topics
        asyncio.create_task(self._subscribe_to_topics())

    async def _subscribe_to_topics(self) -> None:
        """Subscribe to required message topics."""
        try:
            await self._message_broker.subscribe("data/response", self._handle_data_response)
            await self._message_broker.subscribe("data/state", self._handle_data_state)
            await self._message_broker.subscribe("sequence/response", self._handle_sequence_response)
            await self._message_broker.subscribe("sequence/state", self._handle_sequence_state)
            await self._message_broker.subscribe("sequence/step", self._handle_sequence_step)
            await self._message_broker.subscribe("state/change", self._handle_state_change)

            # Load initial sequence list
            await self._load_sequence_library()

        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "sequence_control",
                    "message": f"Failed to subscribe to topics: {e}"
                }
            )

    async def _load_sequence_library(self) -> None:
        """Load available sequences."""
        try:
            request_id = f"seq_list_{datetime.now().timestamp()}"
            logger.info("Requesting sequence list...")
            await self._message_broker.publish(
                "data/request",
                {
                    "request_id": request_id,
                    "request_type": "list",
                    "type": "sequences"
                }
            )
            self._pending_requests[request_id] = "list"
            logger.debug(f"Sent sequence list request: {request_id}")
        except Exception as e:
            logger.error(f"Error requesting sequence list: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "sequence_control",
                    "message": f"Failed to request sequence list: {e}"
                }
            )

    async def _update_sequence_list(self, files: list) -> None:
        """Update sequence list in combo box."""
        try:
            if not isinstance(files, list):
                logger.error(f"Invalid files data type: {type(files)}")
                return

            self.sequence_combo.clear()
            self.sequence_combo.addItem("")  # Blank default option
            self._sequences.clear()  # Clear existing sequences

            for sequence in files:
                if isinstance(sequence, str):
                    name = sequence.replace(".yaml", "")
                    self.sequence_combo.addItem(name)
                    self._sequences[name] = {"name": name}
            
            logger.debug(f"Updated sequence list with {len(self._sequences)} sequences: {list(self._sequences.keys())}")
            
            # Update status only if no sequences found
            if not files:
                self.status_label.setText("Status: No sequences available")
                self.status_label.setStyleSheet("color: gray;")
            else:
                self.status_label.setText("Status: No sequence selected")
                self.status_label.setStyleSheet("color: gray;")

        except Exception as e:
            logger.error(f"Error updating sequence list: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "sequence_control",
                    "message": f"Failed to update sequence list: {e}"
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
                "error",
                {
                    "source": "sequence_control",
                    "message": f"Failed to update button states: {e}"
                }
            )

    async def _handle_data_response(self, data: Dict[str, Any]) -> None:
        """Handle data response messages."""
        try:
            # Verify this response is for sequences
            if data.get("type") != "sequences":
                logger.debug(f"Ignoring non-sequence response: {data.get('type')}")
                return

            # Check if this is a response we're waiting for
            request_id = data.get("request_id")
            if not request_id or request_id not in self._pending_requests:
                logger.debug(f"Ignoring unexpected response ID: {request_id}")
                return

            # Get the request type we were expecting
            expected_type = self._pending_requests.pop(request_id)
            if data.get("request_type") != expected_type:
                logger.warning(f"Mismatched request type for {request_id}")
                return

            if not data.get("success"):
                logger.error(f"Data operation failed: {data.get('error')}")
                self.status_label.setText(f"Error: {data.get('error')}")
                self.status_label.setStyleSheet("color: #e74c3c;")
                return

            if expected_type == "list":
                if "data" in data and "files" in data["data"]:
                    logger.info(f"Received sequence list: {data['data']['files']}")
                    await self._update_sequence_list(data["data"]["files"])
                else:
                    logger.warning(f"Missing files in response data: {data}")
            elif expected_type == "load":
                sequence_data = data.get("data", {})
                if sequence_data:
                    self.start_button.setEnabled(True)
                    self.status_label.setText("Status: Sequence Loaded")
                    self.status_label.setStyleSheet("color: #2980b9;")

        except Exception as e:
            logger.error(f"Error handling data response: {e}")

    async def _handle_data_state(self, data: Dict[str, Any]) -> None:
        """Handle data state messages."""
        try:
            state = data.get("state")
            operation = data.get("operation")
            if operation == "list" and state == "COMPLETED":
                logger.debug("Sequence list operation completed")
            elif operation == "load" and state == "COMPLETED":
                logger.debug("Sequence load operation completed")

        except Exception as e:
            logger.error(f"Error handling data state: {e}")

    async def _handle_sequence_response(self, data: Dict[str, Any]) -> None:
        """Handle sequence response messages."""
        try:
            if not data.get("success"):
                await self._handle_sequence_error(data)

        except Exception as e:
            logger.error(f"Error handling sequence response: {e}")

    async def _handle_sequence_state(self, data: Dict[str, Any]) -> None:
        """Handle sequence state messages."""
        try:
            status = data.get("state", "")
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

    async def _handle_sequence_step(self, data: Dict[str, Any]) -> None:
        """Handle sequence step messages."""
        try:
            percent = data.get("percent", 0)
            step = data.get("step", "")
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"{step} ({percent}%)")

        except Exception as e:
            logger.error(f"Error handling sequence progress: {e}")

    async def _handle_state_change(self, data: Dict[str, Any]) -> None:
        """Handle system state changes."""
        try:
            self._system_state = data.get("state", "STARTUP")
            await self._update_button_states()

        except Exception as e:
            logger.error(f"Error handling state change: {e}")

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
                request_id = f"seq_load_{sequence_name}_{datetime.now().timestamp()}"
                await self._message_broker.publish(
                    "data/request",
                    {
                        "request_id": request_id,
                        "request_type": "load",
                        "type": "sequences",
                        "name": sequence_name
                    }
                )
                self._pending_requests[request_id] = "load"
                logger.debug(f"Sent load request for sequence {sequence_name}: {request_id}")
        except Exception as e:
            logger.error(f"Error loading sequence: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "sequence_control",
                    "message": f"Failed to load sequence: {e}"
                }
            )

    async def _on_start_clicked(self) -> None:
        """Handle start button click."""
        try:
            sequence_name = self.sequence_combo.currentText()
            if not sequence_name:
                return

            await self._message_broker.publish(
                "sequence/request",
                {
                    "request_type": "start",
                    "name": sequence_name
                }
            )
            logger.debug(f"Sent start request for sequence: {sequence_name}")
        except Exception as e:
            logger.error(f"Error starting sequence: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "sequence_control",
                    "message": f"Failed to start sequence: {e}"
                }
            )

    async def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        try:
            await self._message_broker.publish(
                "sequence/request",
                {
                    "request_type": "cancel"
                }
            )
            logger.debug("Sent cancel request")
        except Exception as e:
            logger.error(f"Error canceling sequence: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "sequence_control",
                    "message": f"Failed to cancel sequence: {e}"
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

            # Update status only after loading
            if not has_selection:
                self.status_label.setText("Status: No sequence selected")
                self.status_label.setStyleSheet("color: gray;")

        except Exception as e:
            logger.error(f"Error handling sequence selection: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "error",
                {
                    "source": "sequence_control",
                    "message": f"Failed to handle sequence selection: {e}"
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
                "error",
                {
                    "source": "sequence_control",
                    "message": f"Failed to load sequence library: {e}"
                }
            ))
