"""Editor tab for process sequence editing."""
from typing import Dict, Any, Optional
import logging
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QSplitter,
    QFrame
)
from PySide6.QtCore import Qt

from ..widgets.base_widget import BaseWidget
from ..managers.ui_update_manager import UIUpdateManager
from ..widgets.editor.parameter_editor import ParameterEditor
from ..widgets.editor.pattern_editor import PatternEditor
from ..widgets.editor.sequence_builder import SequenceBuilder
from ..widgets.editor.sequence_visualizer import SequenceVisualizer

logger = logging.getLogger(__name__)


class EditorTab(BaseWidget):
    """Tab for editing process sequences."""

    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        """Initialize editor tab.

        Args:
            ui_manager: UI update manager instance
            parent: Optional parent widget
        """
        super().__init__(
            widget_id="tab_editor",
            ui_manager=ui_manager,
            update_tags=[
                "editor.status",
                "editor.sequence",
                "editor.pattern",
                "editor.parameters"
            ],
            parent=parent
        )

        # Store widget references
        self._parameter_editor: Optional[ParameterEditor] = None
        self._pattern_editor: Optional[PatternEditor] = None
        self._sequence_builder: Optional[SequenceBuilder] = None
        self._sequence_visualizer: Optional[SequenceVisualizer] = None

        self._init_ui()
        logger.info("Editor tab initialized")

    def _init_ui(self) -> None:
        """Initialize the editor tab UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

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

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates from UIUpdateManager."""
        try:
            if "editor.sequence" in data:
                sequence_data = data["editor.sequence"]
                if self._sequence_visualizer is not None:
                    self._sequence_visualizer.update_sequence(sequence_data)

            if "editor.pattern" in data:
                pattern_data = data["editor.pattern"]
                if self._sequence_builder is not None:
                    await self._sequence_builder.add_pattern(pattern_data)

        except Exception as e:
            logger.error(f"Error handling UI update in editor tab: {e}")

    async def cleanup(self) -> None:
        """Clean up editor tab and child widgets."""
        try:
            # Clean up child widgets first
            if self._parameter_editor is not None:
                try:
                    await self._parameter_editor.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up parameter editor: {e}")

            if self._pattern_editor is not None:
                try:
                    await self._pattern_editor.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up pattern editor: {e}")

            if self._sequence_builder is not None:
                try:
                    await self._sequence_builder.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up sequence builder: {e}")

            if self._sequence_visualizer is not None:
                try:
                    await self._sequence_visualizer.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up sequence visualizer: {e}")

            # Then clean up self
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during editor tab cleanup: {e}")
