"""Editor tab for process sequence editing."""
from typing import Any, Dict, Protocol, runtime_checkable, cast
import asyncio

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSplitter, QVBoxLayout, QWidget

from ..managers.ui_update_manager import UIUpdateManager
from ..widgets.base_widget import BaseWidget
from ..widgets.editor.parameter_editor import ParameterEditor
from ..widgets.editor.pattern_editor import PatternEditor
from ..widgets.editor.sequence_builder import SequenceBuilder
from ..widgets.editor.sequence_visualizer import SequenceVisualizer


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
    """Tab for editing process sequences."""

    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        super().__init__(
            widget_id="tab_editor",
            ui_manager=ui_manager,
            update_tags=[
                "editor.status",
                "editor.sequence",
                "editor.pattern",
                "editor.parameters",
                "system.connection"
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

        self._init_ui()
        logger.info("Editor tab initialized")

    def _init_ui(self) -> None:
        """Initialize the editor tab UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 10)

        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Editors
        left_frame = QFrame()
        left_layout = QVBoxLayout()
        left_frame.setLayout(left_layout)

        # Parameter editor
        editor = ParameterEditor(self._ui_manager)
        self._parameter_editor = cast(ParameterEditorProtocol, editor)
        left_layout.addWidget(cast(QWidget, editor))

        # Load available parameter files
        asyncio.create_task(self._load_parameter_files())

        # Pattern editor
        self._pattern_editor = PatternEditor(self._ui_manager)
        left_layout.addWidget(self._pattern_editor)

        # Load available pattern files
        asyncio.create_task(self._load_pattern_files())

        splitter.addWidget(left_frame)

        # Right side - Sequence builder and visualizer
        right_frame = QFrame()
        right_layout = QVBoxLayout()
        right_frame.setLayout(right_layout)

        # Sequence builder
        self._sequence_builder = SequenceBuilder(self._ui_manager)
        right_layout.addWidget(self._sequence_builder)

        # Load available sequence files
        asyncio.create_task(self._load_sequence_files())

        # Sequence visualizer
        self._sequence_visualizer = SequenceVisualizer(self._ui_manager)
        right_layout.addWidget(self._sequence_visualizer)

        splitter.addWidget(right_frame)

        # Set initial splitter sizes
        splitter.setSizes([400, 600])  # 40/60 split

        layout.addWidget(splitter)
        self.setLayout(layout)

    def _update_status_label(self) -> None:
        """Update the status label based on connection state."""
        if self._connected:
            self._status_label.setText("Connected - Using hardware parameters")
        else:
            self._status_label.setText("Disconnected - Using simulated parameters")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates from UIUpdateManager."""
        try:
            if "system.connection" in data:
                was_connected = self._connected
                self._connected = data.get("connected", False)
                if was_connected != self._connected:
                    self._update_status_label()
                    await self._notify_connection_state()

            if "editor.sequence" in data:
                sequence_data = data["editor.sequence"]
                if self._sequence_visualizer is not None:
                    self._sequence_visualizer.update_sequence(sequence_data)

            if "editor.pattern" in data:
                pattern_data = data["editor.pattern"]
                if self._sequence_builder is not None:
                    await self._sequence_builder.add_pattern(pattern_data)

            if "editor.parameters" in data:
                parameters = data.get("editor.parameters", {})
                if self._parameter_editor is not None:
                    # In disconnected mode, use default/simulated parameters
                    if not self._connected:
                        parameters = self._get_simulated_parameters(parameters)
                    await self._parameter_editor.update_parameters(parameters)

        except Exception as e:
            logger.error(f"Error handling UI update in editor tab: {e}")

    def _get_simulated_parameters(self, base_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get simulated parameters when in disconnected mode."""
        try:
            # Start with base parameters
            simulated = base_params.copy()

            # Add default values for common parameters if not present
            defaults = {
                "powder_feed_rate": 2.0,  # g/min
                "carrier_gas_pressure": 30.0,  # psi
                "process_gas_pressure": 40.0,  # psi
                "nozzle_temperature": 400.0,  # °C
                "substrate_temperature": 25.0,  # °C
                "scan_speed": 10.0,  # mm/s
                "layer_height": 0.1,  # mm
                "track_overlap": 0.5,  # ratio
            }

            for key, value in defaults.items():
                if key not in simulated:
                    simulated[key] = value

            return simulated

        except Exception as e:
            logger.error(f"Error generating simulated parameters: {e}")
            return base_params

    async def _notify_connection_state(self) -> None:
        """Notify child widgets of connection state change."""
        try:
            widgets = [
                self._parameter_editor,
                self._pattern_editor,
                self._sequence_builder,
                self._sequence_visualizer
            ]

            for widget in widgets:
                if widget is not None and hasattr(widget, 'handle_connection_change'):
                    await widget.handle_connection_change(self._connected)

        except Exception as e:
            logger.error(f"Error notifying widgets of connection state: {e}")

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

    async def _load_parameter_files(self) -> None:
        """Load available parameter files from disk."""
        try:
            # Get parameter files from config manager
            files = await self._ui_manager.send_update(
                "config/request/list_files",
                {"type": "parameters"}
            )

            if files and isinstance(files, list):
                self._parameter_editor.update_file_list(files)
                logger.debug(f"Loaded parameter files: {files}")
        except Exception as e:
            logger.error(f"Error loading parameter files: {e}")

    async def _load_pattern_files(self) -> None:
        """Load available pattern files from disk."""
        try:
            # Get pattern files from config manager
            files = await self._ui_manager.send_update(
                "config/request/list_files",
                {"type": "patterns"}
            )

            if files and isinstance(files, list):
                self._pattern_editor.update_file_list(files)
                logger.debug(f"Loaded pattern files: {files}")
        except Exception as e:
            logger.error(f"Error loading pattern files: {e}")

    async def _load_sequence_files(self) -> None:
        """Load available sequence files from disk."""
        try:
            # Get sequence files from config manager
            files = await self._ui_manager.send_update(
                "config/request/list_files",
                {"type": "sequences"}
            )

            if files and isinstance(files, list):
                self._sequence_editor.update_file_list(files)
                logger.debug(f"Loaded sequence files: {files}")
        except Exception as e:
            logger.error(f"Error loading sequence files: {e}")
