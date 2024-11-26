"""Pattern editor widget for editing spray patterns."""
from typing import Dict, Any, Optional
import logging
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox,
    QDoubleSpinBox, QComboBox, QLineEdit,
    QFormLayout, QGroupBox, QWidget
)
from PySide6.QtCore import Signal

from ..base_widget import BaseWidget
from ...managers.ui_update_manager import UIUpdateManager

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
        self._connect_signals()
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
        """Initialize the widget UI."""
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
        type_layout.addWidget(QLabel("Pattern Type:"))
        type_layout.addWidget(self._type_combo)
        layout.addLayout(type_layout)
        
        # Parameter editor group
        param_group = QGroupBox("Pattern Parameters")
        self._param_layout = QFormLayout()
        param_group.setLayout(self._param_layout)
        layout.addWidget(param_group)
        
        # Preview group
        preview_group = QGroupBox("Pattern Preview")
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self._save_btn = QPushButton("Save Changes")
        self._reset_btn = QPushButton("Reset")
        control_layout.addWidget(self._save_btn)
        control_layout.addWidget(self._reset_btn)
        layout.addLayout(control_layout)
        
        self.setLayout(layout)

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        self._new_btn.clicked.connect(self._create_new_pattern)
        self._delete_btn.clicked.connect(self._delete_current_pattern)
        self._save_btn.clicked.connect(self._save_changes)
        self._reset_btn.clicked.connect(self._reset_changes)
        self._type_combo.currentTextChanged.connect(self._update_parameter_editor)

    async def _create_new_pattern(self) -> None:
        """Create a new pattern."""
        try:
            await self._ui_manager.send_update(
                "patterns/create",
                {"name": "New Pattern"}
            )
        except Exception as e:
            logger.error(f"Error creating new pattern: {e}")

    async def _delete_current_pattern(self) -> None:
        """Delete current pattern."""
        try:
            if self._current_pattern:
                await self._ui_manager.send_update(
                    "patterns/delete",
                    {"name": self._current_pattern}
                )
        except Exception as e:
            logger.error(f"Error deleting pattern: {e}")

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