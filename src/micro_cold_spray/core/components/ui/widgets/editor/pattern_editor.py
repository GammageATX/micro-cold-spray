"""Pattern editor widget for editing spray patterns."""
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox,
    QMessageBox, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from loguru import logger

from micro_cold_spray.core.components.ui.widgets.base_widget import BaseWidget
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker


class PatternEditor(BaseWidget):
    """Pattern editor widget."""

    def __init__(self, ui_manager: UIUpdateManager, message_broker: MessageBroker, parent=None) -> None:
        """Initialize the pattern editor widget."""
        super().__init__(
            widget_id="widget_editor_pattern",
            ui_manager=ui_manager,
            update_tags=[
                "data/list_files",
                "patterns/created",
                "patterns/updated",
                "patterns/deleted"
            ],
            parent=parent
        )

        self._message_broker = message_broker

        # Create layout
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
        self._pattern_combo.currentTextChanged.connect(self._on_pattern_changed)

        self.setLayout(layout)

        # Initialize state
        self._parameter_widgets = {}
        self._current_file = None
        self._is_new_pattern = False

        # Request initial file list
        asyncio.create_task(self._load_patterns())

    def _reset_form(self) -> None:
        """Reset the form to initial state."""
        # Clear existing parameter widgets
        for widget in self._parameter_widgets.values():
            widget.deleteLater()
        self._parameter_widgets.clear()

        # Clear layout
        while self._params_layout.count():
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Reset state
        self._current_file = None
        self._is_new_pattern = False
        self._save_btn.setEnabled(False)

    async def _on_save_clicked(self) -> None:
        """Handle save button click."""
        try:
            if self._is_new_pattern:
                # Get type and parameters
                pattern_type = self._parameter_widgets["type"].currentText()
                if not pattern_type or pattern_type == "Select Type":
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

                logger.info(f"Saving new pattern: {filename}")
                logger.info(f"Pattern data: {pattern}")

                # Send save request
                await self._ui_manager.send_update(
                    "data/save",
                    {
                        "type": "patterns",
                        "name": filename,
                        "value": pattern,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            elif self._current_file:
                # Save changes to existing pattern
                pattern_type = self._parameter_widgets["type"].currentText()
                pattern = self._build_pattern_data(pattern_type)
                if not pattern:
                    return  # Error already shown

                logger.info(f"Saving existing pattern: {self._current_file}")
                logger.info(f"Pattern data: {pattern}")

                await self._ui_manager.send_update(
                    "data/save",
                    {
                        "type": "patterns",
                        "name": self._current_file,
                        "value": pattern,
                        "timestamp": datetime.now().isoformat()
                    }
                )

        except Exception as e:
            logger.error(f"Error saving pattern: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save pattern: {e}")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "type" in data:
                if data["type"] == "data/list_files":
                    # Handle wrapped message format
                    list_data = data.get("data", {})
                    if list_data.get("type") == "patterns":
                        files = list_data.get("files", [])
                        self._pattern_combo.clear()
                        self._pattern_combo.addItems(files)
                        logger.debug(f"Updated pattern list: {files}")

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    async def _load_patterns(self) -> None:
        """Request pattern list from data manager."""
        try:
            await self._ui_manager.send_update(
                "data/list_files",
                {
                    "type": "patterns"
                }
            )
            logger.debug("Requested pattern list")
        except Exception as e:
            logger.error(f"Error requesting pattern list: {e}")

    def _on_pattern_changed(self, pattern_name: str) -> None:
        """Handle pattern selection change."""
        if not pattern_name:
            self._reset_form()
            return

        self._is_new_pattern = False
        self._current_file = pattern_name
        self._save_btn.setEnabled(False)

        # Request pattern data
        asyncio.create_task(
            self._ui_manager.send_update(
                "data/load",
                {
                    "type": "patterns",
                    "name": pattern_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
        )

    def _get_parameter_definitions(self, pattern_type: str) -> list:
        """Get parameter definitions for pattern type."""
        if pattern_type == "linear":
            return [
                {"name": "length", "type": "float", "default": 2.0, "min": 0.1, "max": 1000.0},
                {"name": "direction", "type": "choice", "choices": ["posX", "negX", "posY", "negY"]}
            ]
        elif pattern_type == "serpentine":
            return [
                {"name": "length", "type": "float", "default": 50.0, "min": 0.1, "max": 1000.0},
                {"name": "width", "type": "float", "default": 30.0, "min": 0.1, "max": 1000.0},
                {"name": "spacing", "type": "float", "default": 2.0, "min": 0.1, "max": 100.0},
                {"name": "direction", "type": "choice", "choices": ["posX", "negX", "posY", "negY"]}
            ]
        elif pattern_type == "spiral":
            return [
                {"name": "diameter", "type": "float", "default": 40.0, "min": 0.1, "max": 1000.0},
                {"name": "pitch", "type": "float", "default": 2.0, "min": 0.1, "max": 100.0},
                {"name": "direction", "type": "choice", "choices": ["CW", "CCW"]}
            ]
        elif pattern_type == "custom":
            return [
                {"name": "points", "type": "table", "columns": ["X", "Y", "Z"]}
            ]
        return []

    def _show_type_parameters(self, pattern_type: str, params: Dict = None) -> None:
        """Show parameters for selected pattern type."""
        try:
            self._clear_form()
            row = self._setup_type_selector(pattern_type) if self._is_new_pattern else 0

            if pattern_type:
                self._setup_pattern_parameters(pattern_type, params, row)

        except Exception as e:
            logger.error(f"Error showing parameters: {e}")
            QMessageBox.warning(self, "Error", f"Failed to show parameters: {e}")

    def _clear_form(self) -> None:
        """Clear all widgets from the form."""
        # Clear existing parameter widgets
        for widget in self._parameter_widgets.values():
            widget.deleteLater()
        self._parameter_widgets.clear()

        # Clear layout
        while self._params_layout.count():
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _setup_type_selector(self, pattern_type: str) -> int:
        """Setup the type selector for new patterns."""
        type_label = QLabel("Type:")
        type_combo = QComboBox()
        type_combo.addItem("Select Type", "")  # Blank default
        type_combo.addItems(["linear", "serpentine", "spiral", "custom"])
        if pattern_type:
            type_combo.setCurrentText(pattern_type)
        type_combo.currentTextChanged.connect(self._on_type_changed)
        self._params_layout.addWidget(type_label, 0, 0)
        self._params_layout.addWidget(type_combo, 0, 1)
        self._parameter_widgets["type"] = type_combo
        return 1  # Return next row index

    def _setup_pattern_parameters(self, pattern_type: str, params: Dict, start_row: int) -> None:
        """Setup the parameters for the selected pattern type."""
        if not pattern_type or pattern_type == "Select Type":
            return

        param_defs = self._get_parameter_definitions(pattern_type)
        row = start_row

        for param in param_defs:
            if param.get("type") == "table":
                row = self._setup_table_parameter(param, params, row)
            else:
                row = self._setup_basic_parameter(param, params, row)

        # Add stretch to bottom
        self._params_layout.setRowStretch(row, 1)

    def _setup_table_parameter(self, param: Dict, params: Dict, row: int) -> int:
        """Setup a table parameter widget."""
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(param["columns"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Add buttons for table manipulation
        btn_layout = QHBoxLayout()
        add_row_btn = QPushButton("Add Row")
        del_row_btn = QPushButton("Delete Row")
        btn_layout.addWidget(add_row_btn)
        btn_layout.addWidget(del_row_btn)

        # Add button handlers
        add_row_btn.clicked.connect(lambda: self._add_table_row(table))
        del_row_btn.clicked.connect(lambda: self._delete_table_row(table))

        # Load existing points if any
        if params and "points" in params:
            points = params["points"]
            table.setRowCount(len(points))
            for i, point in enumerate(points):
                for j, val in enumerate(point):
                    item = QTableWidgetItem(str(val))
                    table.setItem(i, j, item)
        else:
            # Start with one empty row
            self._add_table_row(table)

        # Add to layout
        self._params_layout.addLayout(btn_layout, row, 0, 1, 2)
        row += 1
        self._params_layout.addWidget(table, row, 0, 1, 2)
        self._parameter_widgets[param["name"]] = table

        # Connect table changes to enable save button
        table.itemChanged.connect(lambda: self._save_btn.setEnabled(True))

        return row + 1

    def _setup_basic_parameter(self, param: Dict, params: Dict, row: int) -> int:
        """Setup a basic parameter widget (float or choice)."""
        name = param["name"]
        param_type = param.get("type", "float")

        label = QLabel(name.replace('_', ' ').title())
        label.setToolTip(param.get("description", ""))
        self._params_layout.addWidget(label, row, 0)

        if param_type == "choice":
            widget = QComboBox()
            widget.addItems(param["choices"])
            if params and name in params:
                widget.setCurrentText(str(params[name]))
            widget.currentTextChanged.connect(lambda: self._save_btn.setEnabled(True))
        else:  # float
            widget = QDoubleSpinBox()
            widget.setMinimum(param.get("min", 0.0))
            widget.setMaximum(param.get("max", 1000.0))
            widget.setSingleStep(0.1)
            if params and name in params:
                widget.setValue(float(params[name]))
            else:
                widget.setValue(param.get("default", 0.0))
            widget.valueChanged.connect(lambda: self._save_btn.setEnabled(True))

        self._params_layout.addWidget(widget, row, 1)
        self._parameter_widgets[name] = widget

        return row + 1

    def _add_table_row(self, table: QTableWidget) -> None:
        """Add a new row to the points table."""
        current_rows = table.rowCount()
        table.setRowCount(current_rows + 1)
        for col in range(3):
            item = QTableWidgetItem("0.0")
            table.setItem(current_rows, col, item)

    def _delete_table_row(self, table: QTableWidget) -> None:
        """Delete selected row from points table."""
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
        if table.rowCount() == 0:
            self._add_table_row(table)

    def _on_new_clicked(self) -> None:
        """Handle new pattern button click."""
        self._is_new_pattern = True
        self._current_file = None
        self._show_type_parameters("")  # Show empty form with type selector
        self._save_btn.setEnabled(False)

    def _on_type_changed(self, pattern_type: str) -> None:
        """Handle pattern type change."""
        self._show_type_parameters(pattern_type)
        self._save_btn.setEnabled(pattern_type and pattern_type != "Select Type")

    def _build_pattern_data(self, pattern_type: str) -> Dict:
        """Build pattern data from form values."""
        try:
            pattern = {"type": pattern_type, "params": {}}

            for name, widget in self._parameter_widgets.items():
                if isinstance(widget, QTableWidget):
                    pattern["params"][name] = self._get_table_points(widget)
                elif isinstance(widget, QComboBox):
                    pattern["params"][name] = widget.currentText()
                elif isinstance(widget, QDoubleSpinBox):
                    pattern["params"][name] = widget.value()

            return pattern

        except Exception as e:
            logger.error(f"Error building pattern data: {e}")
            QMessageBox.warning(self, "Error", f"Failed to build pattern data: {e}")
            return None

    def _get_table_points(self, table: QTableWidget) -> List[List[float]]:
        """Get points from table widget."""
        points = []
        for row in range(table.rowCount()):
            point = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item is None or not item.text().strip():
                    continue
                try:
                    point.append(float(item.text()))
                except ValueError:
                    raise ValueError(f"Invalid number in row {row+1}, column {col+1}")
            if len(point) == 3:  # Only add complete points
                points.append(point)
        return points

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
