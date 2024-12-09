"""Sequence builder widget for creating and editing operation sequences."""
import logging
import time
from typing import Any, Dict
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QComboBox, QLabel, QFrame, QWidget, QFormLayout, QSpinBox
)
import asyncio
from datetime import datetime

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget
from ....infrastructure.messaging.message_broker import MessageBroker

logger = logging.getLogger(__name__)


class SequenceBuilder(BaseWidget):
    """Widget for building process sequences."""

    sequence_updated = Signal(dict)  # Emitted when sequence is modified

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        message_broker: MessageBroker,
        parent=None
    ):
        super().__init__(
            widget_id="widget_editor_sequence",
            ui_manager=ui_manager,
            update_tags=["error"],
            parent=parent
        )

        # Store dependencies
        self._message_broker = message_broker

        # Initialize state
        self._current_sequence = None
        self._pending_requests = {}  # Track pending requests by ID
        
        # Initialize UI and connect signals
        self._init_ui()
        self._connect_signals()
        
        # Subscribe to response topics
        asyncio.create_task(self._subscribe_to_topics())
        logger.info("Sequence builder initialized")

    def _init_ui(self) -> None:
        """Initialize the sequence builder UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Create main frame
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame_layout = QVBoxLayout()

        # Title
        title = QLabel("Sequence Builder")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        frame_layout.addWidget(title)

        # Sequence selection
        sequence_layout = QHBoxLayout()
        sequence_label = QLabel("Sequence:")
        self._sequence_combo = QComboBox()
        sequence_layout.addWidget(sequence_label)
        sequence_layout.addWidget(self._sequence_combo)
        frame_layout.addLayout(sequence_layout)

        # Sequence controls
        control_layout = QHBoxLayout()
        self._new_btn = QPushButton("New")
        self._load_btn = QPushButton("Load")
        self._save_btn = QPushButton("Save")
        control_layout.addWidget(self._new_btn)
        control_layout.addWidget(self._load_btn)
        control_layout.addWidget(self._save_btn)
        frame_layout.addLayout(control_layout)

        # Step list
        self._step_list = QListWidget()
        frame_layout.addWidget(self._step_list)

        # Action controls
        action_layout = QHBoxLayout()
        action_label = QLabel("Action:")
        self._action_combo = QComboBox()
        self._add_step_btn = QPushButton("Add Step")
        action_layout.addWidget(action_label)
        action_layout.addWidget(self._action_combo)
        action_layout.addWidget(self._add_step_btn)
        frame_layout.addLayout(action_layout)

        # Step controls
        step_layout = QHBoxLayout()
        self._remove_step_btn = QPushButton("Remove Step")
        self._move_up_btn = QPushButton("Move Up")
        self._move_down_btn = QPushButton("Move Down")
        step_layout.addWidget(self._remove_step_btn)
        step_layout.addWidget(self._move_up_btn)
        step_layout.addWidget(self._move_down_btn)
        frame_layout.addLayout(step_layout)

        frame.setLayout(frame_layout)
        layout.addWidget(frame)
        self.setLayout(layout)

        # Initially disable buttons
        self._save_btn.setEnabled(False)
        self._add_step_btn.setEnabled(False)
        self._remove_step_btn.setEnabled(False)
        self._move_up_btn.setEnabled(False)
        self._move_down_btn.setEnabled(False)

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        self._new_btn.clicked.connect(
            lambda: asyncio.create_task(self._new_sequence())
        )
        self._load_btn.clicked.connect(
            lambda: asyncio.create_task(self._load_sequence())
        )
        self._save_btn.clicked.connect(
            lambda: asyncio.create_task(self._save_sequence())
        )
        self._add_step_btn.clicked.connect(
            lambda: asyncio.create_task(self._add_step())
        )
        self._remove_step_btn.clicked.connect(
            lambda: asyncio.create_task(self._remove_step())
        )
        self._move_up_btn.clicked.connect(
            lambda: asyncio.create_task(self._move_step_up())
        )
        self._move_down_btn.clicked.connect(
            lambda: asyncio.create_task(self._move_step_down())
        )

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "sequence/current" in data:
                sequence = data["sequence/current"]
                self._current_sequence = sequence
                self._update_ui()

            elif "sequence/list" in data:
                sequences = data["sequence/list"]
                self._update_sequence_list(sequences)

            elif "action/list" in data:
                actions = data["action/list"]
                self._action_combo.clear()
                self._action_combo.addItems(actions)

            elif "system/connection" in data:
                connected = data.get("connected", False)
                self._update_button_states(connected)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _update_button_states(self, connected: bool) -> None:
        """Update button enabled states based on connection status."""
        try:
            self._new_btn.setEnabled(True)  # Always allow new sequences
            self._load_btn.setEnabled(True)  # Always allow loading
            self._save_btn.setEnabled(bool(self._current_sequence))
            self._add_step_btn.setEnabled(bool(self._current_sequence))
            self._remove_step_btn.setEnabled(bool(self._current_sequence))
            self._move_up_btn.setEnabled(bool(self._current_sequence))
            self._move_down_btn.setEnabled(bool(self._current_sequence))
        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def _new_sequence(self) -> None:
        """Create a new empty sequence."""
        try:
            self._current_sequence = {
                'metadata': {
                    'name': 'New Sequence',
                    'created': time.time(),
                    'modified': time.time()
                },
                'steps': []
            }
            self._update_ui()
            await self._ui_manager.send_update(
                "sequence/current",
                {
                    "sequence": self._current_sequence
                }
            )
        except Exception as e:
            logger.error(f"Error creating new sequence: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _load_sequence(self) -> None:
        """Request to load a sequence."""
        try:
            request_id = f"sequence_load_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "sequence/request",
                {
                    "request_id": request_id,
                    "request_type": "load_dialog"
                }
            )
            self._pending_requests[request_id] = ("load", None)
            logger.debug(f"Requested sequence load dialog: {request_id}")

        except Exception as e:
            logger.error(f"Error requesting sequence load: {e}")

    async def _save_sequence(self) -> None:
        """Request to save current sequence."""
        try:
            if not self._current_sequence:
                raise ValueError("No sequence to save")

            request_id = f"sequence_save_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "sequence/request",
                {
                    "request_id": request_id,
                    "request_type": "save_dialog",
                    "sequence": self._current_sequence
                }
            )
            self._pending_requests[request_id] = ("save", None)
            logger.debug(f"Requested sequence save dialog: {request_id}")

        except Exception as e:
            logger.error(f"Error requesting sequence save: {e}")

    def _update_ui(self) -> None:
        """Update UI to reflect current sequence."""
        try:
            self._step_list.clear()
            if self._current_sequence:
                for step in self._current_sequence['steps']:
                    self._step_list.addItem(
                        f"{step['action']} - {str(step['parameters'])}"
                    )
                self._save_btn.setEnabled(True)
            else:
                self._save_btn.setEnabled(False)
        except Exception as e:
            logger.error(f"Error updating UI: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def add_pattern(self, pattern_data: Dict[str, Any]) -> None:
        """Add a pattern step to the sequence."""
        try:
            # Create new sequence if none exists
            if self._current_sequence is None:
                await self._new_sequence()

            # Ensure sequence exists after creation attempt
            if self._current_sequence is None:
                raise ValueError("Failed to create new sequence")

            step = {
                'type': 'pattern',
                'action': 'execute_pattern',
                'parameters': {
                    'pattern_name': pattern_data.get('name'),
                    'pattern_type': pattern_data.get('type'),
                    'pattern_params': pattern_data.get('parameters', {})
                }
            }

            self._current_sequence['steps'].append(step)
            self._update_ui()

            # Send update with type checking
            sequence_data = self._current_sequence
            if sequence_data is not None:
                await self._ui_manager.send_update(
                    "sequence/current",
                    sequence_data
                )

        except Exception as e:
            logger.error(f"Error adding pattern to sequence: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during sequence builder cleanup: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _load_initial_data(self) -> None:
        """Load initial sequence list and action list."""
        try:
            # Request sequence list
            request_id = f"sequence_list_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "data/request",
                {
                    "request_id": request_id,
                    "request_type": "list",
                    "type": "sequences"
                }
            )
            self._pending_requests[request_id] = ("list", None)
            logger.debug(f"Requested sequence list: {request_id}")

            # Request action list
            request_id = f"action_list_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "action/request",
                {
                    "request_id": request_id,
                    "request_type": "list"
                }
            )
            self._pending_requests[request_id] = ("action_list", None)
            logger.debug(f"Requested action list: {request_id}")

        except Exception as e:
            logger.error(f"Error loading initial data: {e}")

    def _update_sequence_list(self, sequences: Dict[str, Any]) -> None:
        """Update sequence list in UI."""
        try:
            # Clear existing items
            self._sequence_combo.clear()
            
            # Add empty item first
            self._sequence_combo.addItem("")
            
            # Add sequences
            if sequences:
                for sequence_name in sequences:
                    self._sequence_combo.addItem(sequence_name)
            
            logger.debug(f"Updated sequence list with {len(sequences)} items")
        except Exception as e:
            logger.error(f"Error updating sequence list: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def _add_step(self, step_data: Dict[str, Any]) -> None:
        """Add a step to the sequence."""
        try:
            # Create step widget
            step_widget = QWidget()
            step_layout = QHBoxLayout()
            step_layout.setContentsMargins(2, 2, 2, 2)
            step_layout.setSpacing(5)

            # Step type selection
            type_combo = QComboBox()
            type_combo.addItems(['pattern', 'parameter', 'delay', 'move'])
            
            # Parameters section
            params_widget = QWidget()
            params_layout = QFormLayout()
            params_layout.setContentsMargins(0, 0, 0, 0)
            
            # Add fields based on step type
            if step_data.get('type') == 'pattern':
                type_combo.setCurrentText('pattern')
                
                # Pattern file selection
                pattern_combo = QComboBox()
                pattern_combo.addItems(await self._get_pattern_files())
                if 'file' in step_data:
                    pattern_combo.setCurrentText(step_data['file'])
                params_layout.addRow('Pattern:', pattern_combo)
                
                # Passes input
                passes_spin = QSpinBox()
                passes_spin.setRange(1, 100)
                passes_spin.setValue(step_data.get('passes', 1))
                params_layout.addRow('Passes:', passes_spin)

            elif step_data.get('type') == 'parameter':
                type_combo.setCurrentText('parameter')
                
                # Parameter file selection
                param_combo = QComboBox()
                param_combo.addItems(await self._get_parameter_files())
                if 'file' in step_data:
                    param_combo.setCurrentText(step_data['file'])
                params_layout.addRow('Parameters:', param_combo)

            # Add more step types...

            params_widget.setLayout(params_layout)
            
            # Add to step layout
            step_layout.addWidget(type_combo)
            step_layout.addWidget(params_widget)
            
            # Add delete button
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda: self._remove_step(step_widget))
            step_layout.addWidget(delete_btn)
            
            step_widget.setLayout(step_layout)
            self._steps_layout.addWidget(step_widget)

        except Exception as e:
            logger.error(f"Error adding sequence step: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _subscribe_to_topics(self) -> None:
        """Subscribe to required message topics."""
        try:
            await self._message_broker.subscribe("data/response", self._handle_data_response)
            await self._message_broker.subscribe("data/state", self._handle_data_state)
            await self._message_broker.subscribe("action/response", self._handle_action_response)
            await self._message_broker.subscribe("sequence/state", self._handle_sequence_state)

            # Load initial data
            await self._load_initial_data()

        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")

    async def _handle_data_response(self, data: Dict[str, Any]) -> None:
        """Handle data response messages."""
        try:
            # Verify this response is for sequences
            if data.get("type") != "sequences":
                return

            # Check if this is a response we're waiting for
            request_id = data.get("request_id")
            if not request_id or request_id not in self._pending_requests:
                return

            # Get the request type we were expecting
            expected_type, sequence_name = self._pending_requests.pop(request_id)
            if data.get("request_type") != expected_type:
                logger.warning(f"Mismatched request type for {request_id}")
                return

            if not data.get("success"):
                logger.error(f"Data operation failed: {data.get('error')}")
                return

            if expected_type == "list":
                if "data" in data and "files" in data["data"]:
                    self._update_sequence_list(data["data"]["files"])
            elif expected_type == "load":
                sequence_data = data.get("data", {})
                if sequence_data:
                    self._current_sequence = sequence_data
                    self._update_ui()

        except Exception as e:
            logger.error(f"Error handling data response: {e}")

    async def _handle_sequence_response(self, data: Dict[str, Any]) -> None:
        """Handle sequence operation responses."""
        try:
            request_id = data.get("request_id")
            if not request_id or request_id not in self._pending_requests:
                return

            expected_type, _ = self._pending_requests.pop(request_id)
            if data.get("request_type") != expected_type:
                logger.warning(f"Mismatched request type for {request_id}")
                return

            if not data.get("success"):
                logger.error(f"Sequence operation failed: {data.get('error')}")
                return

            if expected_type == "save":
                logger.info("Sequence saved successfully")
            elif expected_type == "load":
                sequence_data = data.get("data", {})
                if sequence_data:
                    self._current_sequence = sequence_data
                    self._update_ui()

        except Exception as e:
            logger.error(f"Error handling sequence response: {e}")

    async def _get_pattern_files(self) -> list:
        """Get list of available pattern files."""
        try:
            request_id = f"pattern_list_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "data/request",
                {
                    "request_id": request_id,
                    "request_type": "list",
                    "type": "patterns"
                }
            )
            self._pending_requests[request_id] = ("list", None)
            logger.debug(f"Requested pattern list: {request_id}")
            return []  # Return empty list initially, will be updated via response

        except Exception as e:
            logger.error(f"Error getting pattern files: {e}")
            return []

    async def _get_parameter_files(self) -> list:
        """Get list of available parameter files."""
        try:
            request_id = f"parameter_list_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "data/request",
                {
                    "request_id": request_id,
                    "request_type": "list",
                    "type": "parameters"
                }
            )
            self._pending_requests[request_id] = ("list", None)
            logger.debug(f"Requested parameter list: {request_id}")
            return []  # Return empty list initially, will be updated via response

        except Exception as e:
            logger.error(f"Error getting parameter files: {e}")
            return []

    async def _handle_data_state(self, data: Dict[str, Any]) -> None:
        """Handle data state messages."""
        try:
            if data.get("type") not in ["sequences", "actions"]:
                return

            state = data.get("state")
            if state == "loaded":
                # Refresh lists based on type
                request_id = f"{data['type']}_list_{datetime.now().timestamp()}"
                await self._message_broker.publish(
                    "data/request",
                    {
                        "request_id": request_id,
                        "request_type": "list",
                        "type": data["type"]
                    }
                )
                self._pending_requests[request_id] = ("list", None)
                logger.debug(f"Requested {data['type']} list refresh: {request_id}")

        except Exception as e:
            logger.error(f"Error handling data state: {e}")

    async def _handle_sequence_state(self, data: Dict[str, Any]) -> None:
        """Handle sequence state messages."""
        try:
            state = data.get("state")
            if state == "saved":
                # Refresh sequence list
                request_id = f"sequence_list_{datetime.now().timestamp()}"
                await self._message_broker.publish(
                    "data/request",
                    {
                        "request_id": request_id,
                        "request_type": "list",
                        "type": "sequences"
                    }
                )
                self._pending_requests[request_id] = ("list", None)
                logger.debug(f"Requested sequence list refresh after save: {request_id}")

        except Exception as e:
            logger.error(f"Error handling sequence state: {e}")

    async def _handle_action_response(self, data: Dict[str, Any]) -> None:
        """Handle action response messages."""
        try:
            request_id = data.get("request_id")
            if not request_id or request_id not in self._pending_requests:
                return

            expected_type, _ = self._pending_requests.pop(request_id)
            if expected_type != "action_list":
                return

            if not data.get("success"):
                logger.error(f"Action operation failed: {data.get('error')}")
                return

            # Update action combo box
            actions = data.get("actions", [])
            self._action_combo.clear()
            self._action_combo.addItem("")  # Empty default option
            for action in actions:
                self._action_combo.addItem(action)

            logger.debug(f"Updated action list with {len(actions)} actions")

        except Exception as e:
            logger.error(f"Error handling action response: {e}")
