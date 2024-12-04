"""Parameter editor widget for editing process parameters."""
import logging
from typing import Any, Dict, Optional
import asyncio
from datetime import datetime

from PySide6.QtCore import Signal, Qt
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
    QInputDialog,
    QMessageBox,
    QScrollArea,
    QGroupBox,
)
from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


class ParameterEditor(BaseWidget):
    """Widget for editing process parameters."""

    parameter_updated = Signal(dict)  # Emitted when parameters are modified

    # Default parameter definitions based on YAML structure
    DEFAULT_DEFINITIONS = {
        "metadata": {
            "name": {"type": "string", "label": "Name", "default": ""},
            "version": {"type": "string", "label": "Version", "default": "1.0"},
            "created": {
                "type": "string",
                "label": "Created",
                "default": datetime.now().strftime("%Y-%m-%d")
            },
            "author": {"type": "string", "label": "Author", "default": "", "readonly": True},
            "description": {"type": "string", "label": "Description", "default": ""},
        },
        "nozzle": {
            "type": {
                "type": "choice",
                "label": "Type",
                "default": "",
                "choices": []  # Will be populated from nozzles folder
            },
            "diameter": {
                "type": "number",
                "label": "Diameter (mm)",
                "default": 1.78,
                "min": 0.5,
                "max": 3.0,
                "step": 0.01
            },
            "manufacturer": {"type": "string", "label": "Manufacturer", "default": "", "readonly": True},
        },
        "gas_flows": {
            "gas_type": {
                "type": "choice",
                "label": "Gas Type",
                "default": "N2",
                "choices": ["N2", "He", "Ar"]
            },
            "main_gas": {
                "type": "number",
                "label": "Main Gas (SLPM)",
                "default": 50.0,
                "min": 0,
                "max": 100,
                "step": 1
            },
            "feeder_gas": {
                "type": "number",
                "label": "Feeder Gas (SLPM)",
                "default": 5.0,
                "min": 0,
                "max": 10,
                "step": 1
            },
        },
        "powder_feed": {
            "frequency": {
                "type": "number",
                "label": "Frequency (Hz)",
                "default": 600,
                "min": 0,
                "max": 1000,
                "step": 200
            },
            "deagglomerator": {
                "enabled": {
                    "type": "choice",
                    "label": "Deagglomerator Enabled",
                    "default": "true",
                    "choices": ["true", "false"]
                },
                "speed": {
                    "type": "choice",
                    "label": "Deagglomerator Speed",
                    "default": "Medium",
                    "choices": ["Low", "Medium", "High"]
                },
            }
        }
    }

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
                "parameters.definitions",
                "parameters.nozzles",
                "config.hardware",
                "user.current"
            ],
            parent=parent
        )

        self._current_set: Optional[str] = None
        self._parameter_widgets: Dict[str, QWidget] = {}
        self._parameter_definitions = self.DEFAULT_DEFINITIONS
        self._nozzle_specs: Dict[str, Dict[str, Any]] = {}
        self._current_user: Optional[str] = None
        self._deagg_speeds = {
            "off": 35,   # Off state
            "low": 30,   # High speed (inverted duty cycle)
            "medium": 25,  # Medium speed (inverted duty cycle)
            "high": 20    # Low speed (inverted duty cycle)
        }

        self._init_ui()
        # Request initial data
        self._request_initial_data()
        logger.info("Parameter editor initialized")

    def _request_initial_data(self) -> None:
        """Request initial data from the server."""
        # Request parameter list
        asyncio.create_task(self._ui_manager.send_update(
            "parameters/list",
            {}
        ))

        # Request nozzle list
        asyncio.create_task(self._ui_manager.send_update(
            "parameters/nozzles/list",
            {}
        ))

        # Request hardware config for deagglomerator settings
        asyncio.create_task(self._ui_manager.send_update(
            "config/request",
            {
                "type": "hardware",
                "key": "physical.hardware_sets.deagglomerator.speeds"
            }
        ))

        # Request current user
        asyncio.create_task(self._ui_manager.send_update(
            "user/current",
            {}
        ))

    def _update_deagg_speeds(self, config: Dict[str, Any]) -> None:
        """Update deagglomerator speeds from config."""
        try:
            physical = config.get("physical", {})
            hardware_sets = physical.get("hardware_sets", {})
            deagg = hardware_sets.get("deagglomerator", {})
            speeds = deagg.get("speeds", {})

            if speeds:
                self._deagg_speeds = speeds
                logger.debug(f"Updated deagglomerator speeds: {self._deagg_speeds}")
        except Exception as e:
            logger.error(f"Error updating deagglomerator speeds: {e}")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "user.current" in data:
                # Update current user and author field
                self._current_user = data.get("value", "")
                if "metadata.author" in self._parameter_widgets:
                    widget = self._parameter_widgets["metadata.author"]
                    if isinstance(widget, QLineEdit):
                        widget.setText(self._current_user)

            if "parameters.list" in data:
                # Update parameter set list
                sets = data.get("files", [])
                self._set_combo.clear()
                self._set_combo.addItems(sets)

            if "parameters.nozzles" in data:
                # Update nozzle specifications and choices
                self._nozzle_specs = data.get("files", {})
                if "nozzle.type" in self._parameter_widgets:
                    combo = self._parameter_widgets["nozzle.type"]
                    if isinstance(widget, QComboBox):
                        current = combo.currentText()
                        combo.clear()
                        combo.addItems(sorted(self._nozzle_specs.keys()))
                        if current in self._nozzle_specs:
                            combo.setCurrentText(current)

            if "config.update" in data:
                # Update deagglomerator speed mappings from hardware config
                config = data.get("data", {})
                if isinstance(config, dict):
                    self._update_deagg_speeds(config)

            if "parameters.current" in data:
                # Update current parameter values
                params = data.get("value", {})
                self._update_parameter_values(params)

            if "parameters.validation" in data:
                # Handle validation results
                validation = data.get("result", {})
                self._handle_validation_results(validation)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    def _convert_speed_to_percent(self, speed: str) -> int:
        """Convert speed setting to percentage."""
        return self._deagg_speeds.get(speed.lower(), self._deagg_speeds.get("off", 35))

    def _convert_percent_to_speed(self, percent: int) -> str:
        """Convert percentage to speed setting."""
        # Find closest speed setting
        closest = "Off"
        min_diff = float('inf')
        for speed, value in self._deagg_speeds.items():
            diff = abs(value - percent)
            if diff < min_diff:
                min_diff = diff
                closest = speed.title()
        return closest

    def _get_current_values(self) -> Dict[str, Any]:
        """Get current parameter values from UI."""
        values = {}
        try:
            for path, widget in self._parameter_widgets.items():
                # Split path into sections (e.g. "gas_flows.main_gas")
                sections = path.split(".")

                # Get the value based on widget type
                if isinstance(widget, QDoubleSpinBox):
                    value = widget.value()
                elif isinstance(widget, QSpinBox):
                    value = widget.value()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText()
                    # Convert deagglomerator speed to percentage
                    if path == "powder_feed.deagglomerator.speed":
                        value = self._convert_speed_to_percent(value)
                else:
                    value = widget.text()

                # Build nested dictionary structure
                current = values
                for section in sections[:-1]:
                    if section not in current:
                        current[section] = {}
                    current = current[section]
                current[sections[-1]] = value

        except Exception as e:
            logger.error(f"Error getting parameter values: {e}")
        return {"process": values}  # Wrap in process key to match YAML structure

    async def _update_parameter_values(self, parameters: Dict[str, Any]) -> None:
        """Update UI with parameter values."""
        try:
            # Extract process section
            process_params = parameters.get("process", {})
            logger.debug(f"Updating parameter values: {process_params}")

            # Update each widget with its value
            for path, widget in self._parameter_widgets.items():
                # Navigate through nested dictionary
                value = process_params
                for section in path.split("."):
                    value = value.get(section, {})

                if not isinstance(value, dict):
                    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        widget.setValue(float(value))
                    elif isinstance(widget, QComboBox):
                        if path == "powder_feed.deagglomerator.speed":
                            # Convert percentage to speed setting
                            speed = self._convert_percent_to_speed(int(value))
                            widget.setCurrentText(speed)
                        else:
                            widget.setCurrentText(str(value))
                    else:
                        widget.setText(str(value))

        except Exception as e:
            logger.error(f"Error updating parameter values: {e}")

    def _on_nozzle_type_changed(self, nozzle_type: str) -> None:
        """Handle nozzle type selection change."""
        if nozzle_type in self._nozzle_specs:
            specs = self._nozzle_specs[nozzle_type]
            # Update diameter and manufacturer from specs
            if "nozzle.diameter" in self._parameter_widgets:
                widget = self._parameter_widgets["nozzle.diameter"]
                if isinstance(widget, QDoubleSpinBox):
                    widget.setValue(float(specs.get("specifications", {}).get("throat_diameter", 0.24)))

            if "nozzle.manufacturer" in self._parameter_widgets:
                widget = self._parameter_widgets["nozzle.manufacturer"]
                if isinstance(widget, QLineEdit):
                    widget.setText(specs.get("metadata", {}).get("manufacturer", ""))

    def _create_parameter_widget(self, definition: Dict[str, Any]) -> QWidget:
        """Create an appropriate widget based on parameter definition."""
        param_type = definition.get("type", "string")
        default = definition.get("default")
        readonly = definition.get("readonly", False)

        if param_type == "number":
            widget = QDoubleSpinBox()
            widget.setMinimum(definition.get("min", -1000000))
            widget.setMaximum(definition.get("max", 1000000))
            widget.setSingleStep(definition.get("step", 0.1))
            if default is not None:
                widget.setValue(float(default))
            widget.setReadOnly(readonly)

        elif param_type == "choice":
            widget = QComboBox()
            widget.addItems(definition.get("choices", []))
            if default is not None:
                widget.setCurrentText(str(default))
            widget.setEnabled(not readonly)

        else:  # string or unknown type
            widget = QLineEdit()
            if default is not None:
                widget.setText(str(default))
            widget.setReadOnly(readonly)

        return widget

    async def _create_new_set(self) -> None:
        """Create a new parameter set."""
        try:
            # Get new set name from user
            name, ok = QInputDialog.getText(
                self,
                "New Parameter Set",
                "Enter name for new parameter set:"
            )

            if ok and name:
                # Just set up the UI with default values
                self._current_set = name
                # Set author to current user
                if "metadata.author" in self._parameter_widgets:
                    widget = self._parameter_widgets["metadata.author"]
                    if isinstance(widget, QLineEdit):
                        widget.setText(self._current_user or "")
                # Set name in metadata
                if "metadata.name" in self._parameter_widgets:
                    widget = self._parameter_widgets["metadata.name"]
                    if isinstance(widget, QLineEdit):
                        widget.setText(name)
                logger.info(f"Created new parameter set: {name}")

        except Exception as e:
            logger.error(f"Error creating new parameter set: {e}")

    async def _save_changes(self) -> None:
        """Save parameter changes."""
        try:
            if not self._current_set:
                # If no set is selected, create a new one
                await self._create_new_set()
                return

            # Get current values including metadata
            params = self._get_current_values()

            # Ensure author is set
            if not params.get("process", {}).get("metadata", {}).get("author"):
                params["process"]["metadata"]["author"] = self._current_user or ""

            # Save through DataManager
            await self._ui_manager.send_update(
                "parameters/save",
                {
                    "name": self._current_set,
                    "value": params
                }
            )
            logger.info(f"Saved parameters for set: {self._current_set}")

            # Reload to ensure consistency
            await self._ui_manager.send_update(
                "parameters/load",
                {
                    "name": self._current_set
                }
            )

        except Exception as e:
            logger.error(f"Error saving parameters: {e}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save parameter set: {e}"
            )

    def _init_ui(self) -> None:
        """Initialize the parameter editor UI."""
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

        # Parameter form in a scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._form_widget = QWidget()
        self._form_layout = QVBoxLayout()
        self._form_widget.setLayout(self._form_layout)
        scroll.setWidget(self._form_widget)
        layout.addWidget(scroll)

        # Create parameter sections
        self._create_parameter_widgets()

        # Save/Reset buttons
        button_layout = QHBoxLayout()
        self._save_btn = QPushButton("Save Changes")
        self._reset_btn = QPushButton("Reset Changes")
        button_layout.addWidget(self._save_btn)
        button_layout.addWidget(self._reset_btn)
        layout.addLayout(button_layout)

        # Connect signals
        self._new_btn.clicked.connect(self._on_new_clicked)
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        self._set_combo.currentTextChanged.connect(
            lambda text: asyncio.create_task(self._on_set_changed(text))
        )
        self._save_btn.clicked.connect(
            lambda: asyncio.create_task(self._save_changes())
        )
        self._reset_btn.clicked.connect(
            lambda: asyncio.create_task(self._reset_changes())
        )

        # Request initial parameter list
        asyncio.create_task(self._ui_manager.send_update(
            "parameters/list",
            {"timestamp": datetime.now().isoformat()}
        ))

        self.setLayout(layout)

    def _create_parameter_widgets(self) -> None:
        """Create parameter input widgets based on definitions."""
        try:
            # Clear existing widgets
            while self._form_layout.count():
                item = self._form_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._parameter_widgets.clear()

            # Create sections for each parameter group
            for section_name, section_params in self._parameter_definitions.items():
                group = QGroupBox(section_name.replace("_", " ").title())
                form = QFormLayout()

                self._create_section_widgets(section_params, form, parent_key=section_name)

                group.setLayout(form)
                self._form_layout.addWidget(group)

        except Exception as e:
            logger.error(f"Error creating parameter widgets: {e}")

    def _create_section_widgets(self, params: Dict[str, Any], form: QFormLayout, parent_key: str = "") -> None:
        """Create widgets for a parameter section."""
        for name, definition in params.items():
            if isinstance(definition, dict) and "type" not in definition:
                # This is a nested section
                nested_group = QGroupBox(name.replace("_", " ").title())
                nested_form = QFormLayout()
                self._create_section_widgets(definition, nested_form, f"{parent_key}.{name}")
                nested_group.setLayout(nested_form)
                form.addRow(nested_group)
            else:
                # This is a parameter
                full_name = f"{parent_key}.{name}" if parent_key else name
                widget = self._create_parameter_widget(definition)
                form.addRow(definition.get("label", name), widget)
                self._parameter_widgets[full_name] = widget

    def _on_new_clicked(self) -> None:
        """Handle new parameter set button click."""
        asyncio.create_task(self._create_new_set())

    def _on_delete_clicked(self) -> None:
        """Handle delete parameter set button click."""
        asyncio.create_task(self._delete_current_set())

    async def _delete_current_set(self) -> None:
        """Delete the current parameter set."""
        try:
            current = self._set_combo.currentText()
            if not current:
                return

            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Delete Parameter Set",
                f"Are you sure you want to delete '{current}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                await self._ui_manager.send_update(
                    "parameters/delete",
                    {
                        "name": current
                    }
                )

        except Exception as e:
            logger.error(f"Error deleting parameter set: {e}")

    async def _reset_changes(self) -> None:
        """Reset parameters to last saved values."""
        try:
            if self._current_set:
                await self._ui_manager.send_update(
                    "parameters/load",
                    {
                        "name": self._current_set
                    }
                )
        except Exception as e:
            logger.error(f"Error resetting parameters: {e}")

    async def _load_parameter_set(self, set_name: str) -> None:
        """Load a parameter set."""
        try:
            if set_name:
                await self._ui_manager.send_update(
                    "parameters/load",
                    {
                        "name": set_name
                    }
                )
        except Exception as e:
            logger.error(f"Error loading parameter set: {e}")

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

    async def update_file_list(self, files: list[str]) -> None:
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

    async def _on_set_changed(self, set_name: str) -> None:
        """Handle parameter set selection change."""
        try:
            logger.debug(f"Parameter set selection changed to: {set_name}")

            if not set_name:
                logger.debug("No set selected, clearing values")
                self._clear_parameter_values()
                return

            # Load the selected parameter set
            logger.debug(f"Loading parameter set: {set_name}")
            file_path = f"data/parameters/library/{set_name}.yaml"

            # Request file load through UI manager
            response = await self._ui_manager.send_update(
                "parameters/load",
                {
                    "file": file_path,
                    "timestamp": datetime.now().isoformat()
                }
            )
            logger.debug(f"Load response: {response}")

            if response:
                self._current_set = set_name
                # Update UI with loaded values if response contains parameters
                if isinstance(response, dict) and "parameters" in response:
                    await self._update_parameter_values(response["parameters"])
                else:
                    logger.warning(f"Unexpected load response format: {response}")
            else:
                logger.error(f"Failed to load parameter set: {set_name}")

        except Exception as e:
            logger.error(f"Error loading parameter set: {e}", exc_info=True)
            self._clear_parameter_values()  # Reset on error

    def _clear_parameter_values(self) -> None:
        """Clear all parameter input fields."""
        try:
            for widget in self._parameter_widgets.values():
                if isinstance(widget, QDoubleSpinBox):
                    widget.setValue(widget.minimum())
                elif isinstance(widget, QSpinBox):
                    widget.setValue(widget.minimum())
                elif isinstance(widget, QLineEdit):
                    widget.clear()
                elif isinstance(widget, QComboBox):
                    widget.setCurrentIndex(0)
        except Exception as e:
            logger.error(f"Error clearing parameter values: {e}")
