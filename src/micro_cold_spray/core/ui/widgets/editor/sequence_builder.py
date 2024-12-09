"""Sequence builder widget for creating and editing operation sequences."""
import logging
import time
from typing import Any, Dict
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QComboBox, QLabel, QFrame
)
import asyncio

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
            update_tags=[
                "sequence/current",
                "sequence/list",
                "action/list",
                "system/connection",
                "system/error"
            ],
            parent=parent
        )

        # Store dependencies
        self._message_broker = message_broker

        # Initialize state
        self._current_sequence = None
        
        # Initialize UI and connect signals
        self._init_ui()
        self._connect_signals()
        
        # Request initial data
        asyncio.create_task(self._load_initial_data())
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
            await self._ui_manager.send_update(
                "sequence/request",
                {
                    "action": "load_dialog"
                }
            )
        except Exception as e:
            logger.error(f"Error requesting sequence load: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _save_sequence(self) -> None:
        """Request to save current sequence."""
        try:
            if not self._current_sequence:
                raise ValueError("No sequence to save")

            await self._ui_manager.send_update(
                "sequence/request",
                {
                    "action": "save_dialog",
                    "sequence": self._current_sequence
                }
            )
        except Exception as e:
            logger.error(f"Error requesting sequence save: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            )

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
        """Load initial sequence and action data."""
        try:
            # Request sequence list
            await self._ui_manager.send_update(
                "sequence/request",
                {
                    "action": "list"
                }
            )

            # Request action list
            await self._ui_manager.send_update(
                "action/request",
                {
                    "action": "list"
                }
            )

            logger.debug("Requested initial sequence and action data")
        except Exception as e:
            logger.error(f"Error loading initial data: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_builder",
                    "message": str(e),
                    "level": "error"
                }
            )

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
