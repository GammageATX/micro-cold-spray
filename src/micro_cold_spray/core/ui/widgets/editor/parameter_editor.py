"""Parameter editor widget for editing process parameters."""
import logging
from pathlib import Path
import yaml
from typing import Dict, Any, Optional, List
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
from ....infrastructure.config.config_manager import ConfigManager

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
        "Off": 35,
        "Low": 30,
        "Medium": 25,
        "High": 20
    }

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(
            widget_id="widget_editor_parameter",
            ui_manager=ui_manager,
            update_tags=["error"],
            parent=parent
        )

        self._message_broker = message_broker
        self._config_manager = config_manager
        self._current_data: Dict[str, Any] = {}
        self._parameter_widgets: Dict[str, QWidget] = {}
        self._pending_requests = {}  # Track pending requests by ID
        self._nozzle_names = []  # Initialize nozzle list

        self._init_ui()
        
        # Initialize editor
        asyncio.create_task(self._initialize())
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
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        # Create event loop for async operations
        self._loop = asyncio.get_event_loop()

        # Connect signals using lambda to run coroutines
        self._set_combo.currentTextChanged.connect(
            lambda text: self._loop.create_task(self._on_set_selected(text))
        )
        self.new_button.clicked.connect(
            lambda: self._loop.create_task(self._on_new_clicked())
        )
        self.save_button.clicked.connect(
            lambda: self._loop.create_task(self._on_save_clicked())
        )

    def _create_widget_for_value(self, value: Any, key: str = "") -> QWidget:
        """Create appropriate widget based on value type and key."""
        widget = None
        if key == "nozzle":
            widget = QComboBox()
            if not hasattr(self, '_nozzle_names'):  # Add safety check
                self._nozzle_names = []
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
        try:
            process = {}
            for field, widget in self._parameter_widgets.items():
                value = self._get_widget_value(widget)
                process[field] = value
            
            return {
                "process": process
            }
        except Exception as e:
            logger.error(f"Error getting current values: {e}")
            return {}

    def _get_current_user(self) -> str:
        """Get current user from main window."""
        parent_window = self.window()
        if hasattr(parent_window, 'connection_status'):
            return parent_window.connection_status.user_combo.currentText()
        return "Default User"

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            topic, message = next(iter(data.items()))

            if topic == "data/response":
                if not message.get("success"):
                    logger.error(f"Data operation failed: {message.get('error')}")
                    return

                # Check if this is a response we're waiting for
                request_id = message.get("request_id")
                if not request_id or request_id not in self._pending_requests:
                    return

                # Get the expected file type and request type
                file_type, request_type = self._pending_requests.pop(request_id)
                if message.get("type") != file_type or message.get("request_type") != request_type:
                    logger.warning(f"Mismatched response for {request_id}")
                    return

                if file_type == "parameters":
                    if request_type == "list":
                        if "data" in message and "files" in message["data"]:
                            await self._update_parameter_list(message["data"]["files"])
                    elif request_type == "load":
                        if "data" in message:
                            await self._update_parameter_form(message["data"])

                elif file_type == "nozzles":
                    if request_type == "list":
                        if "data" in message and "files" in message["data"]:
                            await self._update_nozzle_list(message["data"]["files"])

            elif topic == "data/state":
                state = message.get("state")
                operation = message.get("operation")
                if operation == "save" and state == "COMPLETED":
                    self.save_button.setEnabled(False)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    async def _initialize(self) -> None:
        """Initialize the editor."""
        try:
            # Request parameter sets
            param_request_id = f"param_list_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "data/request",
                {
                    "request_id": param_request_id,
                    "request_type": "list",
                    "type": "parameters"
                }
            )
            self._pending_requests[param_request_id] = ("parameters", "list")

            # Request nozzle list
            nozzle_request_id = f"nozzle_list_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "data/request",
                {
                    "request_id": nozzle_request_id,
                    "request_type": "list",
                    "type": "nozzles"
                }
            )
            self._pending_requests[nozzle_request_id] = ("nozzles", "list")

        except Exception as e:
            logger.error(f"Error initializing parameter editor: {e}")

    async def _request_parameter_list(self) -> None:
        """Request list of parameter files."""
        try:
            await self._ui_manager.send_update(
                "data/request",
                {
                    "request_type": "list",
                    "type": "parameters"
                }
            )
        except Exception as e:
            logger.error(f"Error requesting parameter list: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "parameter_editor",
                    "message": f"Failed to request parameter list: {e}"
                }
            )

    async def _update_parameter_list(self, files: List[str]) -> None:
        """Update parameter file list in combo box."""
        try:
            self._set_combo.clear()
            self._set_combo.addItem("")  # Add empty option
            
            # Add all yaml files
            for filename in files:
                if filename.endswith(".yaml"):
                    name = filename[:-5]  # Remove .yaml extension
                    self._set_combo.addItem(name)
                    
            logger.debug(f"Updated parameter list with {len(files)} files")
            
        except Exception as e:
            logger.error(f"Error updating parameter list: {e}")

    async def _on_set_selected(self, set_name: str) -> None:
        """Handle parameter set selection."""
        try:
            if not set_name:
                self.save_button.setEnabled(False)
                self._clear_form()
                return

            # Request parameter data
            await self._ui_manager.send_update(
                "data/request",
                {
                    "request_type": "load",
                    "type": "parameters",
                    "name": set_name
                }
            )

        except Exception as e:
            logger.error(f"Error loading parameter set: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "parameter_editor",
                    "message": f"Failed to load parameter set: {e}"
                }
            )

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
                "data/request",
                {
                    "request_type": "save",
                    "type": "parameters",
                    "name": set_name,
                    "data": data
                }
            )

            logger.debug(f"Requested save of parameter set: {set_name}")

        except Exception as e:
            logger.error(f"Error saving parameter set: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "parameter_editor",
                    "message": f"Failed to save parameter set: {e}"
                }
            )

    async def _on_new_clicked(self) -> None:
        """Handle New button click."""
        try:
            # Create empty parameter set with default values matching file format
            self._current_data = {
                "process": {
                    "name": "",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "author": self._get_current_user(),
                    "description": "",
                    "nozzle": "",
                    "main_gas": 50.0,
                    "feeder_gas": 5.0,
                    "frequency": 600,
                    "deagglomerator_speed": 25
                }
            }
            await self._update_form_values(self._current_data)
            self.save_button.setEnabled(True)

        except Exception as e:
            logger.error(f"Error creating new parameter set: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "parameter_editor",
                    "message": f"Failed to create new parameter set: {e}"
                }
            )

    async def _update_form_values(self, data: Dict[str, Any]) -> None:
        """Update form with received parameter data."""
        try:
            self._current_data = data
            self._clear_form()

            # Create form layout
            self._form_widget = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setSpacing(2)
            self._form_widget.setLayout(layout)

            # Create process parameters group
            group = QGroupBox("Process Parameters")
            form = QFormLayout()
            form.setContentsMargins(5, 5, 5, 5)
            form.setSpacing(2)

            # Get process parameters
            process = data.get("process", {})
            if not process:
                logger.warning("No process parameters found in data")
                return

            # Add fields in order
            field_order = [
                "name", "created", "author", "description",
                "nozzle", "main_gas", "feeder_gas", "frequency",
                "deagglomerator_speed"
            ]

            for field in field_order:
                if field in process:
                    label = QLabel(field.replace("_", " ").title())
                    widget = self._create_widget_for_value(process[field], field)
                    self._parameter_widgets[field] = widget
                    form.addRow(label, widget)

            group.setLayout(form)
            layout.addWidget(group)
            self._scroll.setWidget(self._form_widget)
            self.save_button.setEnabled(True)

        except Exception as e:
            logger.error(f"Error updating form values: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "parameter_editor",
                    "message": f"Failed to update form values: {e}"
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

    def _load_nozzle_files(self) -> None:  # Removed async since it's synchronous
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

    async def _save_parameter_set(self, set_name: str) -> None:
        """Save the current parameter set."""
        try:
            if not set_name:
                logger.warning("No parameter set name provided")
                return

            # Get current parameter values from form
            parameters = self._get_form_values()
            
            # Send save request using established protocol
            await self._ui_manager.send_update(
                "parameter/request",
                {
                    "action": "save",
                    "name": set_name,
                    "data": parameters
                }
            )

        except Exception as e:
            logger.error(f"Error saving parameter set: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "parameter_editor",
                    "message": f"Failed to save parameter set: {e}"
                }
            )

    async def _update_validation_rules(self, config: Dict[str, Any]) -> None:
        """Update validation rules when file format config changes."""
        try:
            # Get parameter format specification
            param_format = config.get("parameters", {})
            if not param_format:
                return

            # Update widget validation rules
            for field, spec in param_format.items():
                widget = self._parameter_widgets.get(field)
                if not widget:
                    continue

                if isinstance(widget, QSpinBox):
                    widget.setMinimum(spec.get("min", -1000000))
                    widget.setMaximum(spec.get("max", 1000000))
                elif isinstance(widget, QDoubleSpinBox):
                    widget.setMinimum(spec.get("min", -1000000.0))
                    widget.setMaximum(spec.get("max", 1000000.0))
                    widget.setDecimals(spec.get("decimals", 3))
                elif isinstance(widget, QComboBox):
                    if "choices" in spec:
                        widget.clear()
                        widget.addItems(spec["choices"])

        except Exception as e:
            logger.error(f"Error updating validation rules: {e}")

    async def _update_application_settings(self, config: Dict[str, Any]) -> None:
        """Update settings when application config changes."""
        try:
            # Update paths
            paths = config.get("paths", {})
            if "data" in paths:
                # Update data paths if needed
                pass

            # Update other relevant settings
            services = config.get("services", {})
            if "data_manager" in services:
                # Update data manager settings if needed
                pass

        except Exception as e:
            logger.error(f"Error updating application settings: {e}")

    async def _update_nozzle_list(self, files: List[str]) -> None:
        """Update nozzle choices in combo box."""
        try:
            # Store nozzle names without .yaml extension
            self._nozzle_names = [f.replace(".yaml", "") for f in files]
            logger.debug(f"Updated nozzle list: {self._nozzle_names}")

            # Update any existing nozzle combo boxes
            for widget in self._parameter_widgets.values():
                if isinstance(widget, QComboBox) and widget.count() > 0:
                    current = widget.currentText()
                    widget.clear()
                    widget.addItems(self._nozzle_names)
                    widget.addItem("Add Nozzle...")
                    if current in self._nozzle_names:
                        widget.setCurrentText(current)

        except Exception as e:
            logger.error(f"Error updating nozzle list: {e}")
