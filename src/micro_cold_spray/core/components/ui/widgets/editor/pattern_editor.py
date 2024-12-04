"""Pattern editor widget for editing spray patterns."""
import logging
from typing import Any, Dict, Optional
import asyncio
from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QMessageBox,
)

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


class PatternEditor(BaseWidget):
    """Widget for editing spray patterns."""

    pattern_updated = Signal(dict)  # Emitted when pattern is modified
    pattern_created = Signal(dict)  # Emitted when new pattern is created

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_editor_pattern",
            ui_manager=ui_manager,
            update_tags=[
                "patterns.list",
                "patterns.types",
                "patterns.current",
                "patterns.validation",
                "patterns.parameters"
            ],
            parent=parent
        )

        self._current_pattern: Optional[str] = None
        self._parameter_widgets: Dict[str, QWidget] = {}

        self._init_ui()
        logger.info("Pattern editor initialized")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "patterns.list" in data:
                patterns = data["patterns.list"]
                self._pattern_combo.clear()
                self._pattern_combo.addItems(patterns)

            if "patterns.types" in data:
                types = data["patterns.types"]
                self._type_combo.clear()
                self._type_combo.addItems(types)

            if "patterns.current" in data:
                pattern = data["patterns.current"]
                self._update_pattern_values(pattern)

            if "patterns.validation" in data:
                validation = data["patterns.validation"]
                self._handle_validation_results(validation)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    def _init_ui(self) -> None:
        """Initialize the pattern editor UI."""
        layout = QVBoxLayout()

        # Pattern selection
        selection_layout = QHBoxLayout()
        self._pattern_combo = QComboBox()
        self._new_btn = QPushButton("New Pattern")
        self._delete_btn = QPushButton("Delete Pattern")
        selection_layout.addWidget(QLabel("Pattern:"))
        selection_layout.addWidget(self._pattern_combo)
        selection_layout.addWidget(self._new_btn)
        selection_layout.addWidget(self._delete_btn)
        layout.addLayout(selection_layout)

        # Pattern type selection
        type_layout = QHBoxLayout()
        self._type_combo = QComboBox()
        self._type_combo.addItems(["serpentine", "spiral", "linear", "custom"])
        type_layout.addWidget(QLabel("Type:"))
        type_layout.addWidget(self._type_combo)
        layout.addLayout(type_layout)

        # Save/Reset buttons
        button_layout = QHBoxLayout()
        self._save_btn = QPushButton("Save Changes")
        self._reset_btn = QPushButton("Reset Changes")
        button_layout.addWidget(self._save_btn)
        button_layout.addWidget(self._reset_btn)
        layout.addLayout(button_layout)

        # Connect all signals
        self._new_btn.clicked.connect(self._on_new_clicked)
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        self._pattern_combo.currentTextChanged.connect(self._on_pattern_changed)
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        self._save_btn.clicked.connect(lambda: asyncio.create_task(self._save_changes()))
        self._reset_btn.clicked.connect(lambda: asyncio.create_task(self._reset_changes()))
        self._type_combo.currentTextChanged.connect(
            lambda t: asyncio.create_task(self._update_parameter_editor(t)))

        self.setLayout(layout)

    def _on_new_clicked(self) -> None:
        """Handle new pattern button click."""
        asyncio.create_task(self._create_new_pattern())

    def _on_delete_clicked(self) -> None:
        """Handle delete pattern button click."""
        asyncio.create_task(self._delete_current_pattern())

    async def _create_new_pattern(self) -> None:
        """Create a new pattern."""
        try:
            # Get new pattern name from user
            name, ok = QInputDialog.getText(
                self,
                "New Pattern",
                "Enter name for new pattern:"
            )

            if ok and name:
                pattern_type = self._type_combo.currentText()
                # Create new pattern
                await self._ui_manager.send_update(
                    "patterns/create",
                    {
                        "name": name,
                        "type": pattern_type,
                        "timestamp": datetime.now().isoformat()
                    }
                )

        except Exception as e:
            logger.error(f"Error creating new pattern: {e}")

    async def _delete_current_pattern(self) -> None:
        """Delete the current pattern."""
        try:
            current = self._pattern_combo.currentText()
            if not current:
                return

            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Delete Pattern",
                f"Are you sure you want to delete '{current}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                await self._ui_manager.send_update(
                    "patterns/delete",
                    {
                        "name": current,
                        "timestamp": datetime.now().isoformat()
                    }
                )

        except Exception as e:
            logger.error(f"Error deleting pattern: {e}")

    def _on_pattern_changed(self, pattern_name: str) -> None:
        """Handle pattern selection change."""
        if pattern_name:
            asyncio.create_task(self._load_pattern(pattern_name))

    def _on_type_changed(self, pattern_type: str) -> None:
        """Handle pattern type change."""
        if pattern_type:
            asyncio.create_task(self._update_pattern_type(pattern_type))

    async def _load_pattern(self, pattern_name: str) -> None:
        """Load the selected pattern."""
        try:
            await self._ui_manager.send_update(
                "patterns/load",
                {
                    "name": pattern_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error loading pattern: {e}")

    async def _update_pattern_type(self, pattern_type: str) -> None:
        """Update the current pattern type."""
        try:
            current = self._pattern_combo.currentText()
            if current:
                await self._ui_manager.send_update(
                    "patterns/update_type",
                    {
                        "name": current,
                        "type": pattern_type,
                        "timestamp": datetime.now().isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"Error updating pattern type: {e}")

    async def _save_changes(self) -> None:
        """Save pattern changes."""
        try:
            if self._current_pattern:
                pattern = self._get_current_values()
                await self._ui_manager.send_update(
                    "patterns/save",
                    {
                        "name": self._current_pattern,
                        "pattern": pattern
                    }
                )
        except Exception as e:
            logger.error(f"Error saving pattern: {e}")

    async def _reset_changes(self) -> None:
        """Reset pattern to last saved values."""
        try:
            if self._current_pattern:
                await self._ui_manager.send_update(
                    "patterns/reset",
                    {"name": self._current_pattern}
                )
        except Exception as e:
            logger.error(f"Error resetting pattern: {e}")

    async def _update_parameter_editor(self, pattern_type: str) -> None:
        """Update parameter editor for selected pattern type."""
        try:
            await self._ui_manager.send_update(
                "patterns/type/change",
                {"type": pattern_type}
            )
        except Exception as e:
            logger.error(f"Error updating pattern type: {e}")

    def _update_pattern_values(self, pattern: Dict[str, Any]) -> None:
        """Update UI with pattern values."""
        try:
            for name, value in pattern.items():
                if name in self._parameter_widgets:
                    widget = self._parameter_widgets[name]
                    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        widget.setValue(value)
                    elif isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QComboBox):
                        widget.setCurrentText(str(value))
        except Exception as e:
            logger.error(f"Error updating pattern values: {e}")

    def _get_current_values(self) -> Dict[str, Any]:
        """Get current pattern values from UI."""
        values = {}
        try:
            for name, widget in self._parameter_widgets.items():
                if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    values[name] = widget.value()
                elif isinstance(widget, QLineEdit):
                    values[name] = widget.text()
                elif isinstance(widget, QComboBox):
                    values[name] = widget.currentText()
        except Exception as e:
            logger.error(f"Error getting pattern values: {e}")
        return values

    def _handle_validation_results(self, validation: Dict[str, Any]) -> None:
        """Handle pattern validation results."""
        try:
            for name, result in validation.items():
                if name in self._parameter_widgets:
                    widget = self._parameter_widgets[name]
                    if result.get("valid", True):
                        widget.setStyleSheet("")
                    else:
                        widget.setStyleSheet("background-color: #ffcccc;")
        except Exception as e:
            logger.error(f"Error handling validation results: {e}")

    async def update_file_list(self, files: list[str]) -> None:
        """Update the list of available pattern files.

        Args:
            files: List of pattern file names
        """
        try:
            self._pattern_combo.clear()
            self._pattern_combo.addItems(files)
            logger.debug(f"Updated pattern file list: {files}")
        except Exception as e:
            logger.error(f"Error updating pattern file list: {e}")
