"""Editor tab for process sequence editing."""
from typing import Any, Dict, Protocol, runtime_checkable
import asyncio

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSplitter, QVBoxLayout

from ..managers.ui_update_manager import UIUpdateManager
from ..widgets.base_widget import BaseWidget
from ..widgets.editor.parameter_editor import ParameterEditor
from ..widgets.editor.pattern_editor import PatternEditor
from ..widgets.editor.sequence_builder import SequenceBuilder
from ..widgets.editor.sequence_visualizer import SequenceVisualizer
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager


@runtime_checkable
class ParameterEditorProtocol(Protocol):
    """Protocol for parameter editor interface."""

    async def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Update editor parameters."""
        pass

    async def handle_connection_change(self, connected: bool) -> None:
        """Handle connection state change."""
        pass


class EditorTab(BaseWidget):
    """Editor tab for patterns, parameters and sequences."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        parent=None
    ):
        super().__init__(
            widget_id="tab_editor",
            ui_manager=ui_manager,
            update_tags=[
                "editor/status",
                "editor/sequence",
                "editor/pattern",
                "editor/parameters",
                "system/connection",
                "data/response",
                "system/error"
            ],
            parent=parent
        )

        # Initialize status label first
        self._status_label = QLabel()
        self._status_label.setStyleSheet("color: gray; font-style: italic;")
        self._connected = False

        # Store widget references
        self._parameter_editor = None
        self._pattern_editor = None
        self._sequence_builder = None
        self._sequence_visualizer = None
        self._load_files_task = None

        self._message_broker = message_broker  # Store message broker
        self._config_manager = config_manager  # Store config manager
        self._init_ui()
        logger.info("Editor tab initialized")

    def _init_ui(self) -> None:
        """Initialize UI components."""
        try:
            layout = QVBoxLayout()
            layout.setContentsMargins(10, 5, 10, 10)

            # Add status label
            layout.addWidget(self._status_label)

            # Create main splitter
            splitter = QSplitter(Qt.Horizontal)

            # Left side - Editors
            left_frame = QFrame()
            left_layout = QVBoxLayout()
            left_frame.setLayout(left_layout)

            # Create vertical splitter for parameter and pattern editors
            left_splitter = QSplitter(Qt.Vertical)

            # Parameter editor
            self._parameter_editor = ParameterEditor(
                ui_manager=self._ui_manager,
                message_broker=self._message_broker,
                config_manager=self._config_manager,
                parent=self
            )
            left_splitter.addWidget(self._parameter_editor)

            # Pattern editor
            self._pattern_editor = PatternEditor(
                ui_manager=self._ui_manager,
                message_broker=self._message_broker,
                parent=self
            )
            left_splitter.addWidget(self._pattern_editor)

            # Set initial sizes for left splitter (50/50 split)
            left_splitter.setSizes([300, 300])

            left_layout.addWidget(left_splitter)
            splitter.addWidget(left_frame)

            # Right side - Sequence builder and visualizer
            right_frame = QFrame()
            right_layout = QVBoxLayout()
            right_frame.setLayout(right_layout)

            # Sequence builder
            self._sequence_builder = SequenceBuilder(
                ui_manager=self._ui_manager,
                message_broker=self._message_broker,
                parent=self
            )
            right_layout.addWidget(self._sequence_builder)

            # Sequence visualizer
            self._sequence_visualizer = SequenceVisualizer(
                ui_manager=self._ui_manager,
                message_broker=self._message_broker,
                parent=self
            )
            right_layout.addWidget(self._sequence_visualizer)

            splitter.addWidget(right_frame)

            # Set initial splitter sizes
            splitter.setSizes([400, 600])  # 40/60 split

            layout.addWidget(splitter)
            self.setLayout(layout)

            # Load files after widgets are created
            logger.info("Starting to load editor files...")
            self._load_files_task = asyncio.create_task(self._load_editor_files())
            self._load_files_task.add_done_callback(self._on_files_loaded)

        except Exception as e:
            logger.error(f"Error initializing editor UI: {e}")

    def _on_files_loaded(self, task):
        """Handle completion of file loading task."""
        try:
            task.result()  # This will raise any exceptions that occurred
            logger.info("File loading task completed successfully")
        except Exception as e:
            logger.error(f"File loading task failed: {e}")

    def _update_status_label(self) -> None:
        """Update the status label based on connection state."""
        if self._connected:
            self._status_label.setText("Connected - Hardware validation enabled")
        else:
            self._status_label.setText("Disconnected - Hardware validation disabled")

    async def _handle_data_list(self, data: Dict[str, Any]) -> None:
        """Handle data list updates."""
        data_type = data.get("type")
        files = data.get("files", [])

        if data_type == "parameters":
            # Add empty option first for parameters
            files.insert(0, "")
            if self._parameter_editor is not None:
                self._parameter_editor._set_combo.clear()
                self._parameter_editor._set_combo.addItems(files)
        elif data_type == "patterns":
            if self._pattern_editor is not None:
                self._pattern_editor._pattern_combo.clear()
                self._pattern_editor._pattern_combo.addItems(files)
        elif data_type == "sequences":
            if self._sequence_builder is not None:
                self._sequence_builder._set_combo.clear()
                self._sequence_builder._set_combo.addItems(files)

    async def _handle_connection_change(self, data: Dict[str, Any]) -> None:
        """Handle connection state changes."""
        self._connected = data.get("connected", False)
        self._update_status_label()

        # Only notify sequence builder since it might need to validate against hardware limits
        if self._sequence_builder is not None:
            await self._sequence_builder.handle_connection_change(self._connected)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates from UIUpdateManager."""
        try:
            if "system/connection" in data:
                await self._handle_connection_change(data)

            if "data/response" in data:
                response_data = data["data/response"]
                if response_data.get("success") and "files" in response_data.get("data", {}):
                    await self._handle_data_list(response_data.get("data", {}))

            if "editor/sequence" in data:
                sequence_data = data["editor/sequence"]
                if self._sequence_visualizer is not None:
                    self._sequence_visualizer.update_sequence(sequence_data)

            if "editor/pattern" in data:
                pattern_data = data["editor/pattern"]
                if self._sequence_builder is not None:
                    await self._sequence_builder.add_pattern(pattern_data)

            if "editor/parameters" in data:
                parameters = data.get("editor/parameters", {})
                if self._parameter_editor is not None:
                    await self._parameter_editor.update_parameters(parameters)

        except Exception as e:
            logger.error(f"Error handling UI update in editor tab: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "editor_tab",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def cleanup(self) -> None:
        """Clean up editor tab and child widgets."""
        try:
            # Clean up child widgets first
            widgets = [
                self._parameter_editor,
                self._pattern_editor,
                self._sequence_builder,
                self._sequence_visualizer
            ]

            for widget in widgets:
                if widget is not None:
                    try:
                        await widget.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up widget: {e}")

            # Then clean up self
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during editor tab cleanup: {e}")

    async def _load_editor_files(self) -> None:
        """Request file lists for parameters, patterns and sequences."""
        try:
            # Request parameter files
            await self._ui_manager.send_update(
                "data/request",
                {
                    "request_type": "list",
                    "type": "parameters",
                    "request_id": f"{self._widget_id}_parameters"
                }
            )

            # Request pattern files
            await self._ui_manager.send_update(
                "data/request",
                {
                    "request_type": "list",
                    "type": "patterns",
                    "request_id": f"{self._widget_id}_patterns"
                }
            )

            # Request sequence files
            await self._ui_manager.send_update(
                "data/request",
                {
                    "request_type": "list",
                    "type": "sequences",
                    "request_id": f"{self._widget_id}_sequences"
                }
            )
            logger.info("File list requests sent")

        except Exception as e:
            logger.error(f"Error requesting file lists: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "editor_tab",
                    "message": f"Failed to load files: {str(e)}",
                    "level": "error"
                }
            )

    async def _handle_pattern_selected(self, pattern_data: Dict[str, Any]) -> None:
        """Handle pattern selection."""
        try:
            # Update visualizer
            if self._sequence_visualizer:
                self._sequence_visualizer.update_sequence([{
                    'type': 'pattern',
                    'pattern': pattern_data
                }])
                
            # Update sequence builder if in pattern step
            if self._sequence_builder:
                await self._sequence_builder.update_current_pattern(pattern_data)
                
        except Exception as e:
            logger.error(f"Error handling pattern selection: {e}")

    async def _handle_parameter_selected(self, param_data: Dict[str, Any]) -> None:
        """Handle parameter selection."""
        try:
            # Update sequence builder if in parameter step
            if self._sequence_builder:
                await self._sequence_builder.update_current_parameters(param_data)
                
        except Exception as e:
            logger.error(f"Error handling parameter selection: {e}")
