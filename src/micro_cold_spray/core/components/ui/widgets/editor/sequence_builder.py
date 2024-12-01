"""Sequence builder widget for creating and editing operation sequences."""
import logging
import time
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)
from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


class SequenceBuilder(BaseWidget):
    """Widget for building operation sequences."""

    sequence_updated = Signal(dict)  # Emitted when sequence is modified

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_editor_sequence",
            ui_manager=ui_manager,
            update_tags=[
                "sequences.list",
                "sequences.current",
                "sequences.validation",
                "actions.available",
                "actions.parameters"
            ],
            parent=parent
        )

        self._current_sequence: Optional[Dict[str, Any]] = None
        self._init_ui()
        self._connect_signals()
        logger.info("Sequence builder initialized")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "sequences.list" in data:
                sequences = data["sequences.list"]
                self._update_sequence_list(sequences)

            if "sequences.current" in data:
                sequence = data["sequences.current"]
                self._current_sequence = sequence
                self._update_ui()

            if "actions.available" in data:
                actions = data["actions.available"]
                self._action_combo.clear()
                self._action_combo.addItems(actions)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    def _init_ui(self) -> None:
        """Initialize the widget UI."""
        layout = QVBoxLayout()

        # Sequence controls
        control_layout = QHBoxLayout()
        self._new_btn = QPushButton("New Sequence")
        self._load_btn = QPushButton("Load Sequence")
        self._save_btn = QPushButton("Save Sequence")
        control_layout.addWidget(self._new_btn)
        control_layout.addWidget(self._load_btn)
        control_layout.addWidget(self._save_btn)
        layout.addLayout(control_layout)

        # Step list
        self._step_list = QListWidget()
        layout.addWidget(QLabel("Sequence Steps:"))
        layout.addWidget(self._step_list)

        # Step editor
        editor_layout = QVBoxLayout()
        self._action_combo = QComboBox()
        editor_layout.addWidget(QLabel("Action Type:"))
        editor_layout.addWidget(self._action_combo)

        # Parameter editor
        self._param_layout = QVBoxLayout()
        editor_layout.addLayout(self._param_layout)

        # Step controls
        step_controls = QHBoxLayout()
        self._add_step_btn = QPushButton("Add Step")
        self._remove_step_btn = QPushButton("Remove Step")
        self._move_up_btn = QPushButton("Move Up")
        self._move_down_btn = QPushButton("Move Down")
        step_controls.addWidget(self._add_step_btn)
        step_controls.addWidget(self._remove_step_btn)
        step_controls.addWidget(self._move_up_btn)
        step_controls.addWidget(self._move_down_btn)
        editor_layout.addLayout(step_controls)

        layout.addLayout(editor_layout)
        self.setLayout(layout)

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        self._new_btn.clicked.connect(self._new_sequence)
        self._load_btn.clicked.connect(self._load_sequence)
        self._save_btn.clicked.connect(self._save_sequence)
        self._add_step_btn.clicked.connect(self._add_step)
        self._remove_step_btn.clicked.connect(self._remove_step)
        self._move_up_btn.clicked.connect(self._move_step_up)
        self._move_down_btn.clicked.connect(self._move_step_down)
        self._action_combo.currentTextChanged.connect(
            self._update_parameter_editor)
        self._step_list.currentRowChanged.connect(self._load_step)

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
                "sequences/current",
                self._current_sequence
            )
        except Exception as e:
            logger.error(f"Error creating new sequence: {e}")

    async def _load_sequence(self) -> None:
        """Request to load a sequence."""
        try:
            await self._ui_manager.send_update(
                "sequences/load",
                {"request": "load_dialog"}
            )
        except Exception as e:
            logger.error(f"Error requesting sequence load: {e}")

    async def _save_sequence(self) -> None:
        """Request to save current sequence."""
        try:
            if self._current_sequence:
                await self._ui_manager.send_update(
                    "sequences/save",
                    self._current_sequence
                )
        except Exception as e:
            logger.error(f"Error saving sequence: {e}")

    def _update_ui(self) -> None:
        """Update UI to reflect current sequence."""
        try:
            self._step_list.clear()
            if self._current_sequence:
                for step in self._current_sequence['steps']:
                    self._step_list.addItem(
                        f"{step['action']} - {str(step['parameters'])}"
                    )
        except Exception as e:
            logger.error(f"Error updating UI: {e}")

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
                    "sequences/current",
                    sequence_data
                )

        except Exception as e:
            logger.error(f"Error adding pattern to sequence: {e}")

    # Additional step management methods...
    async def _add_step(self) -> None:
        """Add a new step to the sequence."""
        pass  # Implementation to be added

    async def _remove_step(self) -> None:
        """Remove the selected step from the sequence."""
        pass  # Implementation to be added

    async def _move_step_up(self) -> None:
        """Move the selected step up in the sequence."""
        pass  # Implementation to be added

    async def _move_step_down(self) -> None:
        """Move the selected step down in the sequence."""
        pass  # Implementation to be added

    async def _update_parameter_editor(self, action_type: str) -> None:
        """Update parameter editor for selected action type."""
        pass  # Implementation to be added

    async def _load_step(self, index: int) -> None:
        """Load step data into editor."""
        pass  # Implementation to be added

    def _update_sequence_list(self, sequences: List[str]) -> None:
        """Update the list of available sequences.

        Args:
            sequences: List of sequence names
        """
        try:
            # Store current selection
            current = self._step_list.currentRow()

            # Update list
            self._step_list.clear()
            for sequence in sequences:
                self._step_list.addItem(sequence)

            # Restore selection if valid
            if current >= 0 and current < self._step_list.count():
                self._step_list.setCurrentRow(current)

        except Exception as e:
            logger.error(f"Error updating sequence list: {e}")
