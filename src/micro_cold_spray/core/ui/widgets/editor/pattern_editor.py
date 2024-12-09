"""Pattern editor widget for editing spray patterns."""
from typing import Dict, Any
import asyncio
from datetime import datetime

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
            update_tags=["error"],
            parent=parent
        )

        self._message_broker = message_broker
        self._parameter_widgets = {}
        self._current_file = None
        self._is_new_pattern = False
        self._pending_requests = {}  # Track pending requests by ID

        self._init_ui()
        logger.info("Pattern editor initialized")

        # Subscribe to response topics
        asyncio.create_task(self._subscribe_to_topics())

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
        self._connect_signals()

        self.setLayout(layout)

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        # Create event loop for async operations
        self._loop = asyncio.get_event_loop()

        # Connect signals using lambda to run coroutines
        self._pattern_combo.currentTextChanged.connect(
            lambda text: self._loop.create_task(self._on_pattern_changed(text))
        )
        self._new_btn.clicked.connect(
            lambda: self._loop.create_task(self._on_new_clicked())
        )
        self._save_btn.clicked.connect(
            lambda: self._loop.create_task(self._on_save_clicked())
        )

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "parameter/current" in data:
                parameter_data = data.get("parameter/current", {})
                if isinstance(parameter_data, dict):
                    self._current_data = parameter_data
                    self._update_form()
                    self.save_button.setEnabled(True)
                    logger.debug(f"Updated form with parameter data: {parameter_data}")

            elif "parameter/list" in data:
                file_list = data.get("parameter/list", [])
                if isinstance(file_list, list):
                    self._set_combo.clear()
                    self._set_combo.addItem("")  # Add empty option
                    self._set_combo.addItems(file_list)
                    logger.debug(f"Updated parameter list with {len(file_list)} items")

            elif "system/connection" in data:
                connected = data.get("connected", False)
                self._update_button_states(connected)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "parameter_editor",
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

    async def _on_new_clicked(self) -> None:
        """Handle new button click."""
        try:
            self._is_new_pattern = True
            self._current_file = None
            await self._show_type_parameters("", {})
            self._save_btn.setEnabled(True)
        except Exception as e:
            logger.error(f"Error creating new pattern: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

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
                await self._show_type_parameters("", {})
                return

            self._is_new_pattern = False
            self._current_file = pattern_name

            # Request pattern data
            request_id = f"pattern_load_{pattern_name}_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "data/request",
                {
                    "request_id": request_id,
                    "request_type": "load",
                    "type": "patterns",
                    "name": pattern_name
                }
            )
            self._pending_requests[request_id] = ("load", pattern_name)
            logger.debug(f"Requested pattern load: {request_id}")

        except Exception as e:
            logger.error(f"Error loading pattern: {e}")

    async def _load_patterns(self) -> None:
        """Request pattern list."""
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
        except Exception as e:
            logger.error(f"Error requesting pattern list: {e}")

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

    async def _on_set_selected(self, set_name: str) -> None:
        """Handle parameter set selection."""
        try:
            if not set_name:
                self.save_button.setEnabled(False)
                self._clear_form()
                return

            # Request parameter set data
            await self._ui_manager.send_update(
                "parameter/request",
                {
                    "type": "parameters",
                    "name": set_name,
                    "action": "load"
                }
            )

            logger.debug(f"Requested parameter set: {set_name}")

        except Exception as e:
            logger.error(f"Error loading parameter set: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "parameter_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _show_type_parameters(self, pattern_type: str, data: Dict[str, Any] = None) -> None:
        """Show parameters for selected pattern type."""
        try:
            # Clear existing widgets
            for widget in self._parameter_widgets.values():
                widget.deleteLater()
            self._parameter_widgets.clear()

            # Create type selector if not exists
            if "type" not in self._parameter_widgets:
                type_combo = QComboBox()
                type_combo.addItem("Select Type")
                type_combo.addItems(["Serpentine", "Spiral", "Custom"])
                if pattern_type:
                    type_combo.setCurrentText(pattern_type)
                self._parameter_widgets["type"] = type_combo
                self._params_layout.addWidget(QLabel("Type:"), 0, 0)
                self._params_layout.addWidget(type_combo, 0, 1)

            # Show parameters based on type
            if pattern_type:
                await self._ui_manager.send_update(
                    "pattern/request",
                    {
                        "request_type": "template",
                        "type": pattern_type.lower(),
                        "data": data or {}
                    }
                )

        except Exception as e:
            logger.error(f"Error showing type parameters: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _subscribe_to_topics(self) -> None:
        """Subscribe to required message topics."""
        try:
            await self._message_broker.subscribe("data/response", self._handle_data_response)
            await self._message_broker.subscribe("data/state", self._handle_data_state)

            # Load initial pattern list
            await self._load_patterns()

        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")

    async def _handle_data_response(self, data: Dict[str, Any]) -> None:
        """Handle data response messages."""
        try:
            # Verify this response is for patterns
            if data.get("type") != "patterns":
                return

            # Check if this is a response we're waiting for
            request_id = data.get("request_id")
            if not request_id or request_id not in self._pending_requests:
                return

            # Get the request type we were expecting
            expected_type, pattern_name = self._pending_requests.pop(request_id)
            if data.get("request_type") != expected_type:
                logger.warning(f"Mismatched request type for {request_id}")
                return

            if not data.get("success"):
                logger.error(f"Data operation failed: {data.get('error')}")
                return

            if expected_type == "list":
                if "data" in data and "files" in data["data"]:
                    await self._update_pattern_list(data["data"]["files"])
            elif expected_type == "load":
                pattern_data = data.get("data", {})
                if pattern_data:
                    await self._show_type_parameters(
                        pattern_data.get("type", ""),
                        pattern_data
                    )

        except Exception as e:
            logger.error(f"Error handling data response: {e}")

    async def _update_pattern_list(self, files: list) -> None:
        """Update pattern list in combo box."""
        try:
            self._pattern_combo.clear()
            self._pattern_combo.addItem("")  # Blank default option

            for pattern in files:
                if isinstance(pattern, str):
                    name = pattern.replace(".yaml", "")
                    self._pattern_combo.addItem(name)
            
            logger.debug(f"Updated pattern list with {len(files)} patterns")

        except Exception as e:
            logger.error(f"Error updating pattern list: {e}")

    async def _handle_data_state(self, data: Dict[str, Any]) -> None:
        """Handle data state messages."""
        try:
            if data.get("type") != "patterns":
                return

            state = data.get("state")
            if state == "loaded":
                # Refresh pattern list
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
                logger.debug(f"Requested pattern list refresh: {request_id}")

        except Exception as e:
            logger.error(f"Error handling data state: {e}")

    async def _handle_pattern_state(self, data: Dict[str, Any]) -> None:
        """Handle pattern state messages."""
        try:
            state = data.get("state")
            if state == "saved":
                # Refresh pattern list
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
                logger.debug(f"Requested pattern list refresh after save: {request_id}")

        except Exception as e:
            logger.error(f"Error handling pattern state: {e}")
