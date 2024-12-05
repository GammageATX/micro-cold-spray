"""Pattern editor widget for editing spray patterns."""
import logging
from typing import Any, Dict, List, Optional
import asyncio
from datetime import datetime

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QMessageBox,
    QScrollArea,
    QFrame,
    QGridLayout,
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
                "data.list",
                "patterns.types",
                "patterns.current",
                "patterns.validation",
                "patterns.parameters",
                "patterns.template"
            ],
            parent=parent
        )

        self._current_pattern: Optional[str] = None
        self._parameter_widgets: Dict[str, QWidget] = {}
        self._parameter_defs: Dict[str, List[Dict[str, Any]]] = {}
        self._scroll_area = None
        self._params_frame = None
        self._params_layout = None
        self._is_new_pattern = False

        self._init_ui()
        logger.info("Pattern editor initialized")

    def _init_ui(self) -> None:
        """Initialize the pattern editor UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("Pattern Editor")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Pattern selection row
        pattern_row = QHBoxLayout()
        pattern_row.addWidget(QLabel("Pattern:"))
        self._pattern_combo = QComboBox()
        pattern_row.addWidget(self._pattern_combo, stretch=1)
        
        # Pattern buttons
        self._new_btn = QPushButton("New")
        self._save_btn = QPushButton("Save")
        self._delete_btn = QPushButton("Delete")
        self._save_btn.setEnabled(False)
        
        pattern_row.addWidget(self._new_btn)
        pattern_row.addWidget(self._save_btn)
        pattern_row.addWidget(self._delete_btn)
        layout.addLayout(pattern_row)

        # Pattern type row
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type:"))
        self._type_combo = QComboBox()
        self._type_combo.setEnabled(False)  # Disabled by default
        type_row.addWidget(self._type_combo, stretch=1)
        # Add spacers to align with buttons above
        type_row.addSpacing(self._new_btn.sizeHint().width())
        type_row.addSpacing(self._save_btn.sizeHint().width())
        type_row.addSpacing(self._delete_btn.sizeHint().width())
        layout.addLayout(type_row)

        # Create scrollable parameter area
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)

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
        self._save_btn.clicked.connect(lambda: asyncio.create_task(self._save_changes()))
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        self._pattern_combo.currentTextChanged.connect(self._on_pattern_changed)
        self._type_combo.currentTextChanged.connect(self._on_type_changed)

        self.setLayout(layout)

    def _create_parameter_widget(self, param_def: Dict[str, Any]) -> QWidget:
        """Create appropriate widget based on parameter definition."""
        param_type = param_def.get("type", "string")
        description = param_def.get("description", "")
        default = param_def.get("default")
        options = param_def.get("options", [])

        if param_type == "float":
            widget = QDoubleSpinBox()
            widget.setMinimum(-10000)
            widget.setMaximum(10000)
            widget.setDecimals(3)
            if default is not None:
                widget.setValue(float(default))
            widget.setToolTip(description)
        elif param_type == "int":
            widget = QSpinBox()
            widget.setMinimum(-10000)
            widget.setMaximum(10000)
            if default is not None:
                widget.setValue(int(default))
            widget.setToolTip(description)
        elif param_type == "string" and options:
            widget = QComboBox()
            widget.addItems(options)
            if default is not None:
                widget.setCurrentText(str(default))
            widget.setToolTip(description)
        else:
            widget = QLineEdit()
            if default is not None:
                widget.setText(str(default))
            widget.setToolTip(description)

        # Connect widget's value changed signal to enable save button
        if isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(lambda: self._save_btn.setEnabled(True))
        elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
            widget.valueChanged.connect(lambda: self._save_btn.setEnabled(True))
        elif isinstance(widget, QLineEdit):
            widget.textChanged.connect(lambda: self._save_btn.setEnabled(True))

        return widget

    def _update_parameter_widgets(self, pattern_type: str, values: Dict[str, Any] = None) -> None:
        """Update parameter widgets based on type definition and values."""
        # Clear existing widgets
        for widget in self._parameter_widgets.values():
            widget.setParent(None)
        self._parameter_widgets.clear()

        # Clear layout
        while self._params_layout.count():
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get parameter definitions for this type
        param_defs = self._parameter_defs.get(pattern_type, [])
        if not param_defs:
            logger.warning(f"No parameter definitions found for type: {pattern_type}")
            return

        # Create widgets for each parameter
        row = 0
        for param_def in param_defs:
            name = param_def.get("name")
            if not name:
                continue

            # Create label with units if specified
            label_text = name.replace('_', ' ').title()
            unit = param_def.get("unit")
            if unit and unit != "enum":
                label_text += f" ({unit})"
            label = QLabel(label_text)
            label.setToolTip(param_def.get("description", ""))
            self._params_layout.addWidget(label, row, 0)

            # Create value widget
            widget = self._create_parameter_widget(param_def)
            if values and name in values:
                if isinstance(widget, QComboBox):
                    widget.setCurrentText(str(values[name]))
                elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                    widget.setValue(values[name])
                else:
                    widget.setText(str(values[name]))

            self._params_layout.addWidget(widget, row, 1)
            self._parameter_widgets[name] = widget
            row += 1

    def _get_current_values(self) -> Dict[str, Any]:
        """Get current parameter values."""
        values = {}
        for name, widget in self._parameter_widgets.items():
            if isinstance(widget, QComboBox):
                values[name] = widget.currentText()
            elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                values[name] = widget.value()
            elif isinstance(widget, QLineEdit):
                values[name] = widget.text()
        return values

    def _on_new_clicked(self) -> None:
        """Handle new pattern button click."""
        self._is_new_pattern = True
        self._type_combo.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._pattern_combo.setCurrentText("")
        self._current_pattern = None
        
        # Clear parameters until type is selected
        self._update_parameter_widgets(self._type_combo.currentText())

    async def _save_changes(self) -> None:
        """Save pattern changes."""
        try:
            if self._is_new_pattern:
                # Get new pattern name from user
                name, ok = QInputDialog.getText(
                    self,
                    "New Pattern",
                    "Enter name for new pattern:"
                )

                if ok and name:
                    pattern_type = self._type_combo.currentText()
                    parameters = self._get_current_values()
                    
                    # Create new pattern
                    await self._ui_manager.send_update(
                        "patterns/create",
                        {
                            "name": name,
                            "type": pattern_type,
                            "parameters": parameters,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    self._is_new_pattern = False
                    self._type_combo.setEnabled(False)
                    self._save_btn.setEnabled(False)
                    self._current_pattern = name
            
            elif self._current_pattern:
                # Save changes to existing pattern
                parameters = self._get_current_values()
                await self._ui_manager.send_update(
                    "patterns/save",
                    {
                        "name": self._current_pattern,
                        "parameters": parameters,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                self._save_btn.setEnabled(False)

        except Exception as e:
            logger.error(f"Error saving pattern: {e}")

    def _on_delete_clicked(self) -> None:
        """Handle delete pattern button click."""
        asyncio.create_task(self._delete_current_pattern())

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
                self._current_pattern = None
                self._save_btn.setEnabled(False)

        except Exception as e:
            logger.error(f"Error deleting pattern: {e}")

    def _on_pattern_changed(self, pattern_name: str) -> None:
        """Handle pattern selection change."""
        if pattern_name:
            self._is_new_pattern = False
            self._type_combo.setEnabled(False)
            asyncio.create_task(self._load_pattern(pattern_name))
        else:
            self._current_pattern = None
            self._save_btn.setEnabled(False)

    def _on_type_changed(self, pattern_type: str) -> None:
        """Handle pattern type change."""
        if pattern_type and self._is_new_pattern:
            # Only update parameters if this is a new pattern
            self._update_parameter_widgets(pattern_type)
            self._save_btn.setEnabled(True)

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
            self._current_pattern = pattern_name
        except Exception as e:
            logger.error(f"Error loading pattern: {e}")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "data.list" in data:
                list_data = data["data.list"]
                if list_data.get("type") == "patterns":
                    files = list_data.get("files", [])
                    self._pattern_combo.clear()
                    self._pattern_combo.addItem("")
                    self._pattern_combo.addItems(files)

            if "patterns.types" in data:
                # Store parameter definitions for each type
                types_data = data["patterns.types"]
                for type_name, type_info in types_data.get("types", {}).items():
                    self._parameter_defs[type_name] = type_info.get("parameters", [])
                
                # Update type combo
                pattern_types = list(self._parameter_defs.keys())
                self._type_combo.clear()
                self._type_combo.addItems(pattern_types)

            if "patterns.current" in data:
                pattern = data["patterns.current"]
                pattern_type = pattern.get("type", "")
                if pattern_type:
                    self._type_combo.setCurrentText(pattern_type)
                    self._update_parameter_widgets(
                        pattern_type, 
                        pattern.get("parameters", {})
                    )
                    self._save_btn.setEnabled(False)

            if "patterns.validation" in data:
                validation = data["patterns.validation"]
                self._handle_validation_results(validation)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    def _handle_validation_results(self, validation: Dict[str, Any]) -> None:
        """Handle pattern validation results."""
        try:
            for param_name, result in validation.items():
                if param_name in self._parameter_widgets:
                    widget = self._parameter_widgets[param_name]
                    if result.get("valid", True):
                        widget.setStyleSheet("")
                        widget.setToolTip(widget.toolTip().split("\nError:")[0])
                    else:
                        widget.setStyleSheet("border: 1px solid red;")
                        error = result.get("error", "Invalid value")
                        current_tooltip = widget.toolTip().split("\nError:")[0]
                        widget.setToolTip(f"{current_tooltip}\nError: {error}")
        except Exception as e:
            logger.error(f"Error handling validation results: {e}")

    async def update_file_list(self, files: list[str]) -> None:
        """Update the list of available pattern files."""
        self._pattern_combo.clear()
        self._pattern_combo.addItem("")
        self._pattern_combo.addItems(files)
