"""Pattern editor widget for editing spray patterns."""
from typing import Dict, Any
import asyncio

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox,
    QMessageBox, QFrame, QScrollArea,
)
from loguru import logger

from micro_cold_spray.core.ui.widgets.base_widget import BaseWidget
from micro_cold_spray.core.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker


class PatternEditor(BaseWidget):
    """Pattern editor widget."""

    def __init__(self, ui_manager: UIUpdateManager, message_broker: MessageBroker, parent=None) -> None:
        """Initialize the pattern editor widget."""
        super().__init__(
            widget_id="widget_editor_pattern",
            ui_manager=ui_manager,
            update_tags=[
                "pattern/current",
                "pattern/list",
                "pattern/update",
                "system/connection",
                "system/error"
            ],
            parent=parent
        )

        self._message_broker = message_broker
        self._parameter_widgets = {}
        self._current_file = None
        self._is_new_pattern = False
        self._init_ui()
        logger.info("Pattern editor initialized")

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Pattern selection row
        pattern_row = QHBoxLayout()
        pattern_row.addWidget(QLabel("Pattern:"))
        self._pattern_combo = QComboBox()
        self._pattern_combo.setMinimumWidth(200)
        pattern_row.addWidget(self._pattern_combo, stretch=1)

        # Pattern buttons
        self._new_btn = QPushButton("New")
        self._save_btn = QPushButton("Save")
        self._new_btn.setFixedWidth(80)
        self._save_btn.setFixedWidth(80)
        self._save_btn.setEnabled(False)

        pattern_row.addWidget(self._new_btn)
        pattern_row.addWidget(self._save_btn)
        layout.addLayout(pattern_row)

        # Create scrollable parameter area
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)

        # Create frame for parameters
        self._params_frame = QFrame()
        self._params_layout = QGridLayout()
        self._params_layout.setContentsMargins(0, 0, 0, 0)
        self._params_layout.setSpacing(10)
        self._params_frame.setLayout(self._params_layout)

        # Add params frame to scroll area
        self._scroll_area.setWidget(self._params_frame)
        layout.addWidget(self._scroll_area)

        # Connect signals
        self._new_btn.clicked.connect(self._on_new_clicked)
        self._save_btn.clicked.connect(lambda: asyncio.create_task(self._on_save_clicked()))
        self._pattern_combo.currentTextChanged.connect(
            lambda text: asyncio.create_task(self._on_pattern_changed(text))
        )

        self.setLayout(layout)

        # Request initial pattern list
        asyncio.create_task(self._load_patterns())

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "pattern/current" in data:
                pattern_data = data["pattern/current"]
                if isinstance(pattern_data, dict):
                    pattern_type = pattern_data.get("type", "")
                    self._show_type_parameters(pattern_type, pattern_data)
                    self._save_btn.setEnabled(True)

            elif "pattern/list" in data:
                file_list = data["pattern/list"]
                if isinstance(file_list, list):
                    self._pattern_combo.clear()
                    self._pattern_combo.addItems(file_list)

            elif "system/connection" in data:
                connected = data.get("connected", False)
                self._update_button_states(connected)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _update_button_states(self, connected: bool) -> None:
        """Update button enabled states based on connection status."""
        try:
            self._new_btn.setEnabled(True)  # Always allow new patterns
            self._save_btn.setEnabled(bool(self._current_file) or self._is_new_pattern)
        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_editor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    def _on_new_clicked(self) -> None:
        """Handle new button click."""
        try:
            self._is_new_pattern = True
            self._current_file = None
            self._show_type_parameters("", {})
            self._save_btn.setEnabled(True)
        except Exception as e:
            logger.error(f"Error creating new pattern: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_editor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def _on_save_clicked(self) -> None:
        """Handle save button click."""
        try:
            pattern_type = self._parameter_widgets["type"].currentText()
            if not pattern_type or pattern_type == "Select Type":
                QMessageBox.warning(self, "Error", "Please select a pattern type")
                return

            pattern = self._build_pattern_data(pattern_type)
            if not pattern:
                return  # Error already shown

            if self._is_new_pattern:
                filename = self._generate_filename(pattern)
                if not filename:
                    return  # Error already shown
            else:
                filename = self._current_file

            await self._ui_manager.send_update(
                "pattern/save",
                {
                    "name": filename,
                    "data": pattern
                }
            )

            logger.debug(f"Requested save of pattern: {filename}")

        except Exception as e:
            logger.error(f"Error saving pattern: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _on_pattern_changed(self, pattern_name: str) -> None:
        """Handle pattern selection change."""
        try:
            if not pattern_name:
                self._reset_form()
                return

            self._is_new_pattern = False
            self._current_file = pattern_name

            # Request pattern data
            await self._ui_manager.send_update(
                "pattern/request",
                {
                    "name": pattern_name
                }
            )

            logger.debug(f"Requested pattern: {pattern_name}")

        except Exception as e:
            logger.error(f"Error loading pattern: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _load_patterns(self) -> None:
        """Request pattern list."""
        try:
            await self._ui_manager.send_update(
                "pattern/request/list",
                {}
            )
            logger.debug("Requested pattern list")
        except Exception as e:
            logger.error(f"Error requesting pattern list: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during pattern editor cleanup: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_editor",
                    "message": str(e),
                    "level": "error"
                }
            )
