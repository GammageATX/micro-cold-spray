"""Sequence builder widget for creating and editing operation sequences."""
import logging
import time
from typing import Any, Dict, Optional
from PySide6.QtCore import Signal
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
            widget_id="widget_editor_sequence_builder",
            ui_manager=ui_manager,
            update_tags=[
                "sequence/current",
                "sequence/list",
                "sequence/update",
                "sequence/validation",
                "action/list",
                "action/parameters",
                "system/connection",
                "system/error"
            ],
            parent=parent
        )

        self._message_broker = message_broker
        self._current_sequence: Optional[Dict[str, Any]] = None
        self._init_ui()
        self._connect_signals()
        logger.info("Sequence builder initialized")

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
                self._current_sequence
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
            if self._current_sequence:
                await self._ui_manager.send_update(
                    "sequence/save",
                    self._current_sequence
                )
        except Exception as e:
            logger.error(f"Error saving sequence: {e}")
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
