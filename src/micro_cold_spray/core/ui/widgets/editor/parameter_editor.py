"""Parameter editor widget for editing process parameters."""
import logging
from pathlib import Path
import yaml
from typing import Dict, Any
from datetime import datetime
import asyncio

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget
from ....infrastructure.messaging.message_broker import MessageBroker

logger = logging.getLogger(__name__)


class AddNozzleDialog(QDialog):
    """Dialog for adding a new nozzle."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Nozzle")
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Create input fields
        self.name_edit = QLineEdit()
        self.manufacturer_edit = QLineEdit()
        self.type_edit = QLineEdit()
        self.type_edit.setText("Cold Spray")  # Default value
        self.description_edit = QLineEdit()

        # Add fields to layout
        layout.addRow("Name:", self.name_edit)
        layout.addRow("Manufacturer:", self.manufacturer_edit)
        layout.addRow("Type:", self.type_edit)
        layout.addRow("Description:", self.description_edit)

        # Add buttons
        button_box = QHBoxLayout()
        button_box.setSpacing(5)
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)

        # Connect signals
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        # Add to main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        main_layout.addLayout(layout)
        main_layout.addLayout(button_box)
        self.setLayout(main_layout)

    def get_nozzle_data(self) -> Dict[str, str]:
        """Get the nozzle data from the dialog."""
        return {
            "name": self.name_edit.text(),
            "manufacturer": self.manufacturer_edit.text(),
            "type": self.type_edit.text(),
            "description": self.description_edit.text()
        }


class ParameterEditor(BaseWidget):
    """Widget for editing process parameters."""

    # Deagglomerator speed mapping
    DEAGG_SPEEDS = {
        "Off": 0,
        "Low": 15,
        "Medium": 25,
        "High": 35
    }

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        message_broker: MessageBroker,
        parent=None
    ):
        super().__init__(
            widget_id="widget_editor_parameters",
            ui_manager=ui_manager,
            update_tags=[
                "parameter/current",
                "parameter/list",
                "parameter/update",
                "system/connection",
                "system/error"
            ],
            parent=parent
        )

        self._message_broker = message_broker
        self._current_data: Dict[str, Any] = {}
        self._parameter_widgets: Dict[str, QWidget] = {}  # Track widgets for saving
        self._form_widget = None  # Main form widget
        self._init_ui()
        self._load_parameter_files()
        self._load_nozzle_files()
        logger.info("Parameter editor initialized")

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Parameter Set Selection
        select_layout = QHBoxLayout()
        select_layout.setContentsMargins(0, 0, 0, 0)
        select_layout.setSpacing(5)
        select_label = QLabel("Parameter Set:")
        select_label.setFixedWidth(80)
        self._set_combo = QComboBox()
        self._set_combo.setFixedHeight(24)
        self.new_button = QPushButton("New")
        self.new_button.setFixedHeight(24)
        self.save_button = QPushButton("Save")
        self.save_button.setFixedHeight(24)
        self.save_button.setEnabled(False)  # Disabled until parameters are loaded
        select_layout.addWidget(select_label)
        select_layout.addWidget(self._set_combo, 1)  # Give combo box more space
        select_layout.addWidget(self.new_button)
        select_layout.addWidget(self.save_button)
        layout.addLayout(select_layout)

        # Scroll Area for Parameters
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        layout.addWidget(self._scroll)

        self.setLayout(layout)

        # Connect signals
        self.new_button.clicked.connect(self._on_new_clicked)
        self.save_button.clicked.connect(self._on_save_clicked)
        self._set_combo.currentTextChanged.connect(self._on_set_selected)

    def _create_widget_for_value(self, value: Any, key: str = "") -> QWidget:
        """Create appropriate widget based on value type and key."""
        widget = None
        if key == "nozzle":
            widget = QComboBox()
            widget.addItems(self._nozzle_names)
            widget.addItem("Add Nozzle...")
            if isinstance(value, str) and value in self._nozzle_names:
                widget.setCurrentText(value)
            widget.currentTextChanged.connect(self._on_nozzle_selected)
        elif key == "deagglomerator_speed":
            widget = QComboBox()
            widget.addItems(list(self.DEAGG_SPEEDS.keys()))
            # Find closest speed setting
            if isinstance(value, (int, float)):
                closest = min(self.DEAGG_SPEEDS.items(), key=lambda x: abs(x[1] - value))
                widget.setCurrentText(closest[0])
        elif key == "feeder_frequency":
            widget = QSpinBox()
            widget.setRange(0, 1200)
            widget.setSingleStep(200)
            widget.setValue(int(value))
        elif key in ["main_gas", "feeder_gas"]:
            widget = QDoubleSpinBox()
            widget.setRange(0, 100)
            widget.setDecimals(1)
            widget.setSingleStep(0.1)
            widget.setValue(float(value))
        elif isinstance(value, bool):
            widget = QComboBox()
            widget.addItems(["True", "False"])
            widget.setCurrentText(str(value))
        elif isinstance(value, int):
            widget = QSpinBox()
            widget.setRange(-1000000, 1000000)
            widget.setValue(value)
        elif isinstance(value, float):
            widget = QDoubleSpinBox()
            widget.setRange(-1000000, 1000000)
            widget.setDecimals(3)
            widget.setValue(value)
        else:
            widget = QLineEdit()
            widget.setText(str(value))

        if widget:
            widget.setFixedHeight(24)
        return widget

    def _get_widget_value(self, widget: QWidget) -> Any:
        """Get value from a widget based on its type."""
        if isinstance(widget, QComboBox):
            text = widget.currentText()
            # Handle deagglomerator speed conversion
            if text in self.DEAGG_SPEEDS:
                return self.DEAGG_SPEEDS[text]
            return text
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget.value()
        elif isinstance(widget, QLineEdit):
            return widget.text()
        return None

    def _get_current_values(self) -> Dict[str, Any]:
        """Get current values from all widgets."""
        values = {}
        for path, widget in self._parameter_widgets.items():
            values[path] = self._get_widget_value(widget)
        return {"process": values}

    def _get_current_user(self) -> str:
        """Get current user from main window."""
        parent_window = self.window()
        if hasattr(parent_window, 'connection_status'):
            return parent_window.connection_status.user_combo.currentText()
        return "Default User"

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "parameter/current" in data:
                parameter_data = data["parameter/current"]
                if isinstance(parameter_data, dict):
                    self._current_data = parameter_data
                    self._update_form()
                    self.save_button.setEnabled(True)

            elif "parameter/list" in data:
                file_list = data["parameter/list"]
                if isinstance(file_list, list):
                    self._set_combo.clear()
                    self._set_combo.addItem("")  # Add empty option
                    for name in file_list:
                        self._set_combo.addItem(name)

            elif "system/connection" in data:
                connected = data.get("connected", False)
                self._update_button_states(connected)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "parameter_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _update_button_states(self, connected: bool) -> None:
        """Update button enabled states based on connection status."""
        try:
            self.new_button.setEnabled(True)  # Always allow new parameters
            self.save_button.setEnabled(bool(self._current_data))  # Enable if we have data
        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "parameter_editor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def _on_new_clicked(self) -> None:
        """Handle New button click."""
        try:
            # Create empty parameter set with default values
            self._current_data = {
                "process": {
                    "name": "",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "author": self._get_current_user(),
                    "description": "",
                    "nozzle": "",
                    "main_gas": 50.0,
                    "feeder_gas": 5.0,
                    "feeder_frequency": 600,
                    "deagglomerator_speed": 25
                }
            }
            self._update_form()
            self.save_button.setEnabled(True)

        except Exception as e:
            logger.error(f"Error creating new parameter set: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "parameter_editor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def _on_save_clicked(self) -> None:
        """Handle Save button click."""
        try:
            # Get the name from the form
            name_widget = self._parameter_widgets.get("name")
            if not name_widget or not name_widget.text():
                QMessageBox.warning(self, "Save Error", "Please enter a name for the parameter set.")
                return

            set_name = name_widget.text().lower().replace(" ", "_")

            # Get current values
            data = self._get_current_values()

            # Send save request
            await self._ui_manager.send_update(
                "parameter/save",
                {
                    "name": set_name,
                    "data": data
                }
            )

            logger.debug(f"Requested save of parameter set: {set_name}")

        except Exception as e:
            logger.error(f"Error saving parameter set: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "parameter_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _on_set_selected(self, set_name: str) -> None:
        """Handle parameter set selection."""
        try:
            if not set_name:
                self.save_button.setEnabled(False)
                self._clear_form()
                return

            # Request parameter set data
            await self._ui_manager.send_update(
                "parameter/request",
                {
                    "name": set_name
                }
            )

            logger.debug(f"Requested parameter set: {set_name}")

        except Exception as e:
            logger.error(f"Error loading parameter set: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "parameter_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _on_nozzle_selected(self, text: str) -> None:
        """Handle nozzle selection."""
        if text == "Add Nozzle...":
            dialog = AddNozzleDialog(self)
            if dialog.exec():
                nozzle_data = dialog.get_nozzle_data()
                self._save_new_nozzle(nozzle_data)
                # Refresh nozzle list
                self._load_nozzle_files()
                # Update combo box
                combo = self._parameter_widgets.get("nozzle")
                if combo and isinstance(combo, QComboBox):
                    combo.clear()
                    combo.addItems(self._nozzle_names)
                    combo.addItem("Add Nozzle...")
                    combo.setCurrentText(nozzle_data["name"])

    def _save_new_nozzle(self, nozzle_data: Dict[str, str]) -> None:
        """Save a new nozzle file."""
        try:
            name = nozzle_data["name"].lower().replace(" ", "_")
            file_path = Path("data/parameters/nozzles") / f"{name}.yaml"

            # Create nozzles directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Save nozzle file
            with open(file_path, 'w') as f:
                yaml.safe_dump({"nozzle": nozzle_data}, f, sort_keys=False)

            logger.debug(f"Saved new nozzle: {name}")

        except Exception as e:
            logger.error(f"Error saving nozzle file: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save nozzle file: {e}")

    def _clear_form(self) -> None:
        """Clear the parameter form."""
        # Remove old form widget if it exists
        if self._form_widget is not None:
            self._form_widget.deleteLater()
            self._form_widget = None

        # Clear widget tracking
        self._parameter_widgets.clear()

    def _update_form(self) -> None:
        """Update form with current parameter values."""
        try:
            self._clear_form()

            # Create new form widget with a single group box
            self._form_widget = QWidget()
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(2, 2, 2, 2)
            main_layout.setSpacing(2)
            self._form_widget.setLayout(main_layout)

            group = QGroupBox("Process Parameters")
            group.setStyleSheet("""
                QGroupBox {
                    margin-top: 5px;
                    padding-top: 10px;
                    padding-bottom: 2px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 3px;
                }
            """)
            form = QFormLayout()
            form.setContentsMargins(5, 5, 5, 5)
            form.setSpacing(2)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

            # Get process parameters
            process = self._current_data.get("process", {})
            if not process:
                logger.warning("No process parameters found in file")
                return

            # Add parameters in a flat structure
            for key, value in process.items():
                label = QLabel(key.replace("_", " ").title())
                label.setFixedHeight(24)
                widget = self._create_widget_for_value(value, key)
                label.setToolTip(key)
                widget.setToolTip(str(value))
                self._parameter_widgets[key] = widget
                form.addRow(label, widget)

            group.setLayout(form)
            main_layout.addWidget(group)

            # Set the form widget in scroll area
            self._scroll.setWidget(self._form_widget)
            logger.debug("Updated parameter form")

        except Exception as e:
            logger.error(f"Error updating form: {e}")

    def _load_parameter_files(self) -> None:
        """Load parameter files from data/parameters directory."""
        try:
            # Get list of yaml files in data/parameters
            param_dir = Path("data/parameters")
            if not param_dir.exists():
                logger.error(f"Parameters directory not found: {param_dir}")
                return

            # Clear combobox
            self._set_combo.clear()
            self._set_combo.addItem("")  # Add empty option

            # Add all yaml files
            for file_path in param_dir.glob("*.yaml"):
                if file_path.parent == param_dir:  # Only files in root directory
                    name = file_path.stem  # Get filename without extension
                    self._set_combo.addItem(name)

            logger.debug(f"Loaded {self._set_combo.count()-1} parameter files")

        except Exception as e:
            logger.error(f"Error loading parameter files: {e}")

    def _load_nozzle_files(self) -> None:
        """Load nozzle files and populate the list of nozzle names."""
        try:
            self._nozzle_names = []
            nozzle_dir = Path("data/parameters/nozzles")

            if nozzle_dir.exists():
                for file_path in nozzle_dir.glob("*.yaml"):
                    with open(file_path, 'r') as f:
                        data = yaml.safe_load(f)
                        if data and "nozzle" in data and "name" in data["nozzle"]:
                            self._nozzle_names.append(data["nozzle"]["name"])

            self._nozzle_names.sort()
            logger.debug(f"Loaded {len(self._nozzle_names)} nozzle files")

        except Exception as e:
            logger.error(f"Error loading nozzle files: {e}")
            self._nozzle_names = []

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during parameter editor cleanup: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "parameter_editor",
                    "message": str(e),
                    "level": "error"
                }
            )
