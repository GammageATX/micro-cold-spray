"""Pattern editor widget for editing spray patterns."""
from typing import Any, Dict, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox,
    QLineEdit, QTextEdit, QMessageBox, QFrame, QScrollArea,
    QWidget
)
from PySide6.QtCore import Qt
from loguru import logger

from ..base_widget import BaseWidget
from ...managers.ui_update_manager import UIUpdateManager


class PatternEditor(BaseWidget):
    """Pattern editor widget."""

    def __init__(self, ui_manager: UIUpdateManager, parent=None) -> None:
        """Initialize the pattern editor."""
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
        self._parameter_widgets = {}
        self._current_file = None
        self._is_new_pattern = True
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
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
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._pattern_combo.currentTextChanged.connect(self._on_pattern_changed)

        self.setLayout(layout)

    def _get_parameter_definitions(self, pattern_type: str) -> list:
        """Get parameter definitions for the given pattern type."""
        if pattern_type == "serpentine":
            return [
                {"name": "length", "type": "float", "description": "Pattern length in mm"},
                {"name": "width", "type": "float", "description": "Pattern width in mm"},
                {"name": "spacing", "type": "float", "description": "Line spacing in mm"},
                {"name": "direction", "type": "string", 
                 "options": ["posX", "negX", "posY", "negY"],
                 "description": "Primary direction of motion"}
            ]
        elif pattern_type == "spiral":
            return [
                {"name": "diameter", "type": "float", "description": "Total diameter in mm"},
                {"name": "pitch", "type": "float", "description": "Distance between revolutions in mm"},
                {"name": "direction", "type": "string", 
                 "options": ["CW", "CCW"],
                 "description": "Spiral direction"}
            ]
        elif pattern_type == "linear":
            return [
                {"name": "length", "type": "float", "description": "Pattern length in mm"},
                {"name": "direction", "type": "string", 
                 "options": ["posX", "negX", "posY", "negY"],
                 "description": "Direction of motion"}
            ]
        elif pattern_type == "custom":
            return [
                {"name": "name", "type": "string", "description": "Custom pattern name"},
                {"name": "points", "type": "points", 
                 "description": "List of points [x, y, z] relative to start"}
            ]
        return []

    def _create_parameter_widget(self, param: Dict[str, Any], values: Dict[str, Any]) -> QWidget:
        """Create a widget for the given parameter."""
        name = param["name"]
        param_type = param["type"]

        if param_type == "float":
            widget = QDoubleSpinBox()
            widget.setMinimum(0)  # All dimensions are positive
            widget.setMaximum(1000)
            widget.setDecimals(3)
            if values and name in values:
                widget.setValue(float(values[name]))
        elif param_type == "points":
            widget = QTextEdit()
            widget.setPlaceholderText("[[x1, y1, z1], [x2, y2, z2], ...]\nAll coordinates relative to (0,0,0)")
            if values and name in values:
                points = values[name]
                text = "\n".join(
                    f"[{p['position'][0]}, {p['position'][1]}, {p['position'][2]}]"
                    for p in points
                )
                widget.setText(text)
        elif param_type == "string" and "options" in param:
            widget = QComboBox()
            widget.addItems(param["options"])
            if values and name in values:
                widget.setCurrentText(values[name])
        else:
            widget = QLineEdit()
            if values and name in values:
                widget.setText(str(values[name]))

        widget.setToolTip(param.get("description", ""))
        return widget

    def _show_type_parameters(self, pattern_type: str, values: Dict[str, Any] = None) -> None:
        """Show parameters for the selected pattern type."""
        # Clear existing widgets
        for widget in self._parameter_widgets.values():
            widget.deleteLater()
        self._parameter_widgets.clear()

        # Clear layout
        while self._params_layout.count():
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row = 0

        # Add type selector for new patterns
        if self._is_new_pattern:
            type_label = QLabel("Type:")
            type_combo = QComboBox()
            type_combo.addItem("Select Type", "")  # Blank default
            type_combo.addItems(["serpentine", "spiral", "linear", "custom"])
            if pattern_type:
                type_combo.setCurrentText(pattern_type)
            type_combo.currentTextChanged.connect(self._on_type_changed)
            self._params_layout.addWidget(type_label, row, 0)
            self._params_layout.addWidget(type_combo, row, 1)
            self._parameter_widgets["type"] = type_combo
            row += 1

        # Get and add parameter widgets
        params = self._get_parameter_definitions(pattern_type)
        for param in params:
            name = param["name"]
            
            # Create label
            label = QLabel(name.replace('_', ' ').title())
            label.setToolTip(param.get("description", ""))
            self._params_layout.addWidget(label, row, 0)

            # Create and add widget
            widget = self._create_parameter_widget(param, values)
            self._params_layout.addWidget(widget, row, 1)
            self._parameter_widgets[name] = widget

            # Connect widget's value changed signal to enable save button
            if isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(lambda: self._save_btn.setEnabled(True))
            elif isinstance(widget, QDoubleSpinBox):
                widget.valueChanged.connect(lambda: self._save_btn.setEnabled(True))
            elif isinstance(widget, (QLineEdit, QTextEdit)):
                widget.textChanged.connect(lambda: self._save_btn.setEnabled(True))

            row += 1

    def _on_new_clicked(self) -> None:
        """Handle new pattern button click."""
        self._is_new_pattern = True
        self._save_btn.setEnabled(False)  # Disable until type is selected
        self._pattern_combo.setCurrentText("")
        self._current_file = None
        self._show_type_parameters("")  # Show blank type selector

    def _on_type_changed(self, pattern_type: str) -> None:
        """Handle pattern type change."""
        if self._is_new_pattern:
            if pattern_type:  # Only show parameters if a type is selected
                self._show_type_parameters(pattern_type)
                self._save_btn.setEnabled(True)
            else:
                self._save_btn.setEnabled(False)

    def _on_pattern_changed(self, pattern_name: str) -> None:
        """Handle pattern selection change."""
        if pattern_name:
            self._is_new_pattern = False
            self._load_pattern(pattern_name)
        else:
            self._current_file = None
            self._save_btn.setEnabled(False)
            self._show_type_parameters("")

    async def _load_pattern(self, pattern_name: str) -> None:
        """Load the selected pattern."""
        try:
            await self._ui_manager.send_update(
                "patterns/load",
                {
                    "filename": pattern_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            self._current_file = pattern_name
        except Exception as e:
            logger.error(f"Error loading pattern: {e}")

    async def _on_save_clicked(self) -> None:
        """Handle save button click."""
        try:
            if self._is_new_pattern:
                # Get type and parameters
                pattern_type = self._parameter_widgets["type"].currentText()
                if not pattern_type:
                    QMessageBox.warning(self, "Error", "Please select a pattern type")
                    return

                # Build pattern data
                pattern = self._build_pattern_data(pattern_type)
                if not pattern:
                    return  # Error already shown

                # Generate filename
                filename = self._generate_filename(pattern)
                if not filename:
                    return  # Error already shown

                # Send save request
                await self._ui_manager.send_update(
                    "patterns/save",
                    {
                        "filename": filename,
                        "pattern": pattern,
                        "timestamp": datetime.now().isoformat()
                    }
                )

                # Reset UI
                self._pattern_combo.setCurrentText("")
                self._show_type_parameters("")
                self._save_btn.setEnabled(False)
                self._current_file = None
                self._is_new_pattern = True

            elif self._current_file:
                # Save changes to existing pattern
                pattern_type = self._parameter_widgets["type"].currentText()
                pattern = self._build_pattern_data(pattern_type)
                if not pattern:
                    return  # Error already shown

                await self._ui_manager.send_update(
                    "patterns/save",
                    {
                        "filename": self._current_file,
                        "pattern": pattern,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                self._save_btn.setEnabled(False)

        except Exception as e:
            logger.error(f"Error saving pattern: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save pattern: {e}")

    def _build_pattern_data(self, pattern_type: str) -> Optional[Dict]:
        """Build pattern data from widgets."""
        try:
            pattern = {
                "type": pattern_type,
                "params": {}
            }

            for name, widget in self._parameter_widgets.items():
                if name == "type":
                    continue
                if isinstance(widget, QDoubleSpinBox):
                    pattern["params"][name] = widget.value()
                elif isinstance(widget, QComboBox):
                    pattern["params"][name] = widget.currentText()
                elif isinstance(widget, QTextEdit) and name == "points":
                    points_text = widget.toPlainText().strip()
                    points = []
                    if points_text:
                        point_lines = [line.strip() for line in points_text.split('\n') if line.strip()]
                        for line in point_lines:
                            coords = [float(x.strip()) for x in line.strip('[]').split(',')]
                            if len(coords) != 3:
                                raise ValueError(f"Invalid point format: {line}")
                            points.append({"position": coords})
                    pattern["params"][name] = points
                elif isinstance(widget, QLineEdit):
                    pattern["params"][name] = widget.text()

            return pattern
        except Exception as e:
            logger.error(f"Error building pattern data: {e}")
            QMessageBox.warning(self, "Error", str(e))
            return None

    def _generate_filename(self, pattern: Dict) -> Optional[str]:
        """Generate filename from pattern data."""
        try:
            pattern_type = pattern["type"]
            params = pattern["params"]
            
            if pattern_type == "linear":
                return f"linear_{params['length']}mm-{params['direction']}"
            elif pattern_type == "serpentine":
                return f"serpentine_{params['spacing']}mm-{params['length']}mm-{params['direction']}"
            elif pattern_type == "spiral":
                return f"spiral_{params['pitch']}mm-{params['diameter']}mm-{params['direction']}"
            elif pattern_type == "custom":
                return params.get("name", "custom_pattern")
            else:
                return "pattern"
        except Exception as e:
            logger.error(f"Error generating filename: {e}")
            QMessageBox.warning(self, "Error", f"Failed to generate filename: {e}")
            return None

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "data.list" in data:
                list_data = data["data.list"]
                if list_data.get("type") == "patterns":
                    files = list_data.get("files", [])
                    self._pattern_combo.clear()
                    self._pattern_combo.addItem("")  # Add empty option
                    self._pattern_combo.addItems(files)
                    logger.debug(f"Updated pattern list with {len(files)} patterns")

            if "patterns.loaded" in data:
                pattern_data = data["patterns.loaded"]["pattern"]
                pattern_type = pattern_data["type"]
                params = pattern_data.get("params", {})
                if pattern_type == "custom":
                    params = {"points": pattern_data["points"]}
                self._show_type_parameters(pattern_type, params)
                logger.debug(f"Loaded pattern of type: {pattern_type}")

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
