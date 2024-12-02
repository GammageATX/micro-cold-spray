"""Parameter editor widget for editing process parameters."""
import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


class ParameterEditor(BaseWidget):
    """Widget for editing process parameters."""

    parameter_updated = Signal(dict)  # Emitted when parameters are modified

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_editor_parameters",
            ui_manager=ui_manager,
            update_tags=[
                "parameters.sets",
                "parameters.current",
                "parameters.validation",
                "parameters.definitions"
            ],
            parent=parent
        )

        self._current_set: Optional[str] = None
        self._parameter_widgets: Dict[str, QWidget] = {}

        self._init_ui()
        self._connect_signals()
        logger.info("Parameter editor initialized")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "parameters.sets" in data:
                # Update parameter set list
                sets = data["parameters.sets"]
                self._set_combo.clear()
                self._set_combo.addItems(sets)

            if "parameters.current" in data:
                # Update current parameter values
                params = data["parameters.current"]
                self._update_parameter_values(params)

            if "parameters.validation" in data:
                # Handle validation results
                validation = data["parameters.validation"]
                self._handle_validation_results(validation)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    def _init_ui(self) -> None:
        """Initialize the widget UI."""
        layout = QVBoxLayout()

        # Parameter set selection
        selection_layout = QHBoxLayout()
        self._set_combo = QComboBox()
        self._new_btn = QPushButton("New Set")
        self._delete_btn = QPushButton("Delete Set")
        selection_layout.addWidget(QLabel("Parameter Set:"))
        selection_layout.addWidget(self._set_combo)
        selection_layout.addWidget(self._new_btn)
        selection_layout.addWidget(self._delete_btn)
        layout.addLayout(selection_layout)

        # Parameter editor form
        self._form_layout = QFormLayout()
        layout.addLayout(self._form_layout)

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
        self._new_btn.clicked.connect(self._create_new_set)
        self._delete_btn.clicked.connect(self._delete_current_set)
        self._save_btn.clicked.connect(self._save_changes)
        self._reset_btn.clicked.connect(self._reset_changes)
        self._set_combo.currentTextChanged.connect(self._load_parameter_set)

    async def _create_new_set(self) -> None:
        """Create a new parameter set."""
        try:
            await self._ui_manager.send_update(
                "parameters/create",
                {"name": "New Parameter Set"}
            )
        except Exception as e:
            logger.error(f"Error creating new parameter set: {e}")

    async def _delete_current_set(self) -> None:
        """Delete the current parameter set."""
        try:
            if self._current_set:
                await self._ui_manager.send_update(
                    "parameters/delete",
                    {"name": self._current_set}
                )
        except Exception as e:
            logger.error(f"Error deleting parameter set: {e}")

    async def _save_changes(self) -> None:
        """Save parameter changes."""
        try:
            if self._current_set:
                params = self._get_current_values()
                await self._ui_manager.send_update(
                    "parameters/save",
                    {
                        "name": self._current_set,
                        "parameters": params
                    }
                )
        except Exception as e:
            logger.error(f"Error saving parameters: {e}")

    async def _reset_changes(self) -> None:
        """Reset parameters to last saved values."""
        try:
            if self._current_set:
                await self._ui_manager.send_update(
                    "parameters/reset",
                    {"name": self._current_set}
                )
        except Exception as e:
            logger.error(f"Error resetting parameters: {e}")

    async def _load_parameter_set(self, set_name: str) -> None:
        """Load a parameter set."""
        try:
            if set_name:
                await self._ui_manager.send_update(
                    "parameters/load",
                    {"name": set_name}
                )
                self._current_set = set_name
        except Exception as e:
            logger.error(f"Error loading parameter set: {e}")

    def _update_parameter_values(self, params: Dict[str, Any]) -> None:
        """Update UI with parameter values."""
        try:
            for name, value in params.items():
                if name in self._parameter_widgets:
                    widget = self._parameter_widgets[name]
                    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        widget.setValue(value)
                    elif isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QComboBox):
                        widget.setCurrentText(str(value))
        except Exception as e:
            logger.error(f"Error updating parameter values: {e}")

    def _get_current_values(self) -> Dict[str, Any]:
        """Get current parameter values from UI."""
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
            logger.error(f"Error getting parameter values: {e}")
        return values

    def _handle_validation_results(self, validation: Dict[str, Any]) -> None:
        """Handle parameter validation results."""
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

    def update_file_list(self, files: list[str]) -> None:
        """Update the list of available parameter files.

        Args:
            files: List of parameter file names
        """
        try:
            self._set_combo.clear()
            self._set_combo.addItems(files)
            logger.debug(f"Updated parameter file list: {files}")
        except Exception as e:
            logger.error(f"Error updating parameter file list: {e}")
