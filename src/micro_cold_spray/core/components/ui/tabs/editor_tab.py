"""Editor tab for process sequence editing."""
from typing import Any, Dict, Protocol, runtime_checkable
import asyncio
from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSplitter, QVBoxLayout

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
        try:
            layout = QVBoxLayout()
            layout.setContentsMargins(10, 5, 10, 10)

            # Create main splitter
            splitter = QSplitter(Qt.Orientation.Horizontal)

            # Left side - Editors
            left_frame = QFrame()
            left_layout = QVBoxLayout()
            left_frame.setLayout(left_layout)

            # Parameter editor
            self._parameter_editor = ParameterEditor(self._ui_manager)
            left_layout.addWidget(self._parameter_editor)

            # Pattern editor
            self._pattern_editor = PatternEditor(self._ui_manager)
            left_layout.addWidget(self._pattern_editor)

            splitter.addWidget(left_frame)

            # Right side - Sequence builder and visualizer
            right_frame = QFrame()
            right_layout = QVBoxLayout()
            right_frame.setLayout(right_layout)

            # Sequence builder
            self._sequence_builder = SequenceBuilder(self._ui_manager)
            right_layout.addWidget(self._sequence_builder)

            # Sequence visualizer
            self._sequence_visualizer = SequenceVisualizer(self._ui_manager)
            right_layout.addWidget(self._sequence_visualizer)

            splitter.addWidget(right_frame)

            # Set initial splitter sizes
            splitter.setSizes([400, 600])  # 40/60 split

            layout.addWidget(splitter)
            self.setLayout(layout)

            # Load files after widgets are created
            logger.debug("Loading editor files...")
            asyncio.create_task(self._load_editor_files())

        except Exception as e:
            logger.error(f"Error initializing editor UI: {e}")

    def _update_status_label(self) -> None:
        """Update the status label based on connection state."""
        if self._connected:
            self._status_label.setText("Connected - Hardware validation enabled")
        else:
            self._status_label.setText("Disconnected - Hardware validation disabled")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates from UIUpdateManager."""
        try:
            if "system.connection" in data:
                # Only notify child widgets that need hardware state
                # Don't disable any editor functionality
                self._connected = data.get("connected", False)
                self._update_status_label()

                # Only notify sequence builder since it might need to validate against hardware limits
                if self._sequence_builder is not None:
                    await self._sequence_builder.handle_connection_change(self._connected)

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
                    # Always pass parameters directly - no simulation needed
                    await self._parameter_editor.update_parameters(parameters)

        except Exception as e:
            logger.error(f"Error handling UI update in editor tab: {e}")

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
        """Load all editor files."""
        try:
            # Load files in parallel
            await asyncio.gather(
                self._load_parameter_files(),
                self._load_pattern_files(),
                self._load_sequence_files()
            )
            logger.info("Editor files loaded successfully")
        except Exception as e:
            logger.error(f"Error loading editor files: {e}")

    async def _load_parameter_files(self) -> None:
        """Load available parameter files from disk."""
        try:
            logger.debug("Loading parameter files directly...")
            param_path = Path("data/parameters/library")

            if not param_path.exists():
                logger.error(f"Parameter directory not found: {param_path}")
                return

            # Get all yaml files in the directory
            parameter_files = [
                f.stem for f in param_path.glob("*.yaml")
                if f.is_file() and "nozzles" not in str(f)
            ]

            if parameter_files:
                logger.info(f"Found parameter sets: {parameter_files}")
                # Add empty option first
                parameter_files.insert(0, "")
                await self._parameter_editor.update_file_list(parameter_files)
            else:
                logger.warning("No parameter files found")
                # Still add blank option
                await self._parameter_editor.update_file_list([""])

        except Exception as e:
            logger.error(f"Error loading parameter files: {e}", exc_info=True)

    async def _load_pattern_files(self) -> None:
        """Load available pattern files from disk."""
        try:
            logger.debug("Loading pattern files directly...")
            pattern_path = Path("data/patterns/library")

            if not pattern_path.exists():
                logger.error(f"Pattern directory not found: {pattern_path}")
                return

            # Get all yaml files recursively
            pattern_files = []
            for subdir in ["serpentine", "spiral"]:
                subpath = pattern_path / subdir
                if subpath.exists():
                    pattern_files.extend([
                        f"{subdir}/{f.stem}" for f in subpath.glob("*.yaml")
                        if f.is_file()
                    ])

            if pattern_files:
                logger.info(f"Found patterns: {pattern_files}")
                await self._pattern_editor.update_file_list(pattern_files)
            else:
                logger.warning("No pattern files found")

        except Exception as e:
            logger.error(f"Error loading pattern files: {e}", exc_info=True)

    async def _load_sequence_files(self) -> None:
        """Load available sequence files from disk."""
        try:
            logger.debug("Loading sequence files directly...")
            seq_path = Path("data/sequences/library")

            if not seq_path.exists():
                logger.error(f"Sequence directory not found: {seq_path}")
                return

            # Get all yaml files in the directory
            sequence_files = [
                f.stem for f in seq_path.glob("*.yaml")
                if f.is_file()
            ]

            if sequence_files:
                logger.info(f"Found sequences: {sequence_files}")
                await self._sequence_builder.update_file_list(sequence_files)
            else:
                logger.warning("No sequence files found")

        except Exception as e:
            logger.error(f"Error loading sequence files: {e}", exc_info=True)
