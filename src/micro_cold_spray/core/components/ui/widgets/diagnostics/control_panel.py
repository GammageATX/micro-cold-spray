"""Manual hardware control widget."""
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QDoubleSpinBox, QCheckBox,
    QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt

from ..base_widget import BaseWidget
from ...managers.ui_update_manager import UIUpdateManager

logger = logging.getLogger(__name__)

class ControlPanel(BaseWidget):
    """Manual hardware control panel."""
    
    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_diagnostics_control",
            ui_manager=ui_manager,
            update_tags=[
                "hardware.status",
                "hardware.valve_states",
                "hardware.flow_values",
                "hardware.feeder_speed",
                "hardware.error"
            ],
            parent=parent
        )
        
        # Track hardware state
        self._valve_states: Dict[str, bool] = {}
        self._flow_values: Dict[str, float] = {}
        self._feeder_speed: float = 0.0
        self._hardware_enabled = False
        
        # Store widget references
        self._valve_controls: Dict[str, QCheckBox] = {}
        self._flow_controls: Dict[str, QDoubleSpinBox] = {}
        self._feeder_speed_control: Optional[QDoubleSpinBox] = None
        self._enable_button: Optional[QPushButton] = None
        self._estop_button: Optional[QPushButton] = None
        
        self._init_ui()
        logger.info("Control panel initialized")

    def _init_ui(self) -> None:
        """Initialize the control panel UI."""
        layout = QVBoxLayout()
        
        # Hardware enable control
        enable_group = QGroupBox("Hardware Control")
        enable_layout = QHBoxLayout()
        
        self._enable_button = QPushButton("Enable Hardware")
        self._enable_button.setCheckable(True)
        self._enable_button.clicked.connect(self._on_enable_clicked)
        
        self._estop_button = QPushButton("EMERGENCY STOP")
        self._estop_button.setStyleSheet("background-color: red; color: white;")
        self._estop_button.clicked.connect(self._on_estop_clicked)
        
        enable_layout.addWidget(self._enable_button)
        enable_layout.addWidget(self._estop_button)
        enable_group.setLayout(enable_layout)
        layout.addWidget(enable_group)
        
        # Add valve controls
        valve_group = QGroupBox("Valve Controls")
        valve_layout = QFormLayout()
        
        for valve in ["gate_partial", "gate_full", "mechanical_pump", "booster_pump"]:
            checkbox = QCheckBox()
            checkbox.clicked.connect(lambda state, v=valve: self._on_valve_clicked(v, state))
            self._valve_controls[valve] = checkbox
            valve_layout.addRow(valve.replace("_", " ").title(), checkbox)
            
        valve_group.setLayout(valve_layout)
        layout.addWidget(valve_group)
        
        # Add flow controls
        flow_group = QGroupBox("Flow Controls")
        flow_layout = QFormLayout()
        
        for flow in ["main", "feeder"]:
            spin = QDoubleSpinBox()
            spin.setRange(0, 100)
            spin.setSingleStep(0.1)
            spin.valueChanged.connect(lambda value, f=flow: self._on_flow_changed(f, value))
            self._flow_controls[flow] = spin
            flow_layout.addRow(f"{flow.title()} Flow (SLPM):", spin)
            
        flow_group.setLayout(flow_layout)
        layout.addWidget(flow_group)
        
        # Add feeder control
        feeder_group = QGroupBox("Powder Feeder")
        feeder_layout = QFormLayout()
        
        self._feeder_speed_control = QDoubleSpinBox()
        self._feeder_speed_control.setRange(0, 100)
        self._feeder_speed_control.setSingleStep(1.0)
        self._feeder_speed_control.valueChanged.connect(self._on_feeder_changed)
        feeder_layout.addRow("Feeder Speed (%):", self._feeder_speed_control)
        
        feeder_group.setLayout(feeder_layout)
        layout.addWidget(feeder_group)
        
        self.setLayout(layout)
        
        # Initially disable controls
        self._update_enabled_state(False)

    def _update_enabled_state(self, enabled: bool) -> None:
        """Update enabled state of all controls."""
        self._hardware_enabled = enabled
        
        # Update button state
        if self._enable_button:
            self._enable_button.setChecked(enabled)
            self._enable_button.setText("Disable Hardware" if enabled else "Enable Hardware")
        
        # Update control states
        for control in self._valve_controls.values():
            control.setEnabled(enabled)
        for control in self._flow_controls.values():
            control.setEnabled(enabled)
        if self._feeder_speed_control:
            self._feeder_speed_control.setEnabled(enabled)

    def _update_valve_states(self, states: Dict[str, bool]) -> None:
        """Update valve control states."""
        for valve, state in states.items():
            if valve in self._valve_controls:
                self._valve_controls[valve].setChecked(state)
                self._valve_states[valve] = state

    def _update_flow_values(self, values: Dict[str, float]) -> None:
        """Update flow control values."""
        for flow, value in values.items():
            if flow in self._flow_controls:
                self._flow_controls[flow].setValue(value)
                self._flow_values[flow] = value

    def _update_feeder_speed(self, speed: float) -> None:
        """Update feeder speed control."""
        if self._feeder_speed_control:
            self._feeder_speed_control.setValue(speed)
            self._feeder_speed = speed

    def _handle_hardware_error(self, error: str) -> None:
        """Handle hardware error."""
        QMessageBox.critical(
            self,
            "Hardware Error",
            f"Hardware error occurred: {error}"
        )

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "hardware.status" in data:
                status = data["hardware.status"]
                self._update_enabled_state(status.get("enabled", False))
                
            if "hardware.valve_states" in data:
                states = data["hardware.valve_states"]
                self._update_valve_states(states)
                
            if "hardware.flow_values" in data:
                values = data["hardware.flow_values"]
                self._update_flow_values(values)
                
            if "hardware.feeder_speed" in data:
                speed = data["hardware.feeder_speed"]
                self._update_feeder_speed(speed)
                
            if "hardware.error" in data:
                error = data["hardware.error"]
                self._handle_hardware_error(error)
                
        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    async def _on_enable_clicked(self, checked: bool) -> None:
        """Handle enable button click."""
        try:
            await self._ui_manager.send_update(
                "hardware/enable",
                {"enabled": checked}
            )
        except Exception as e:
            logger.error(f"Error changing hardware state: {e}")
            self._update_enabled_state(False)

    async def _on_estop_clicked(self) -> None:
        """Handle emergency stop."""
        try:
            await self._ui_manager.send_update(
                "hardware/emergency_stop",
                {
                    "timestamp": datetime.now().isoformat(),
                    "source": "control_panel"
                }
            )
        except Exception as e:
            logger.error(f"Error handling emergency stop: {e}")

    async def _on_valve_clicked(self, valve: str, state: bool) -> None:
        """Handle valve state change."""
        try:
            await self._ui_manager.send_update(
                "hardware/valve/set",
                {
                    "valve": valve,
                    "state": state
                }
            )
        except Exception as e:
            logger.error(f"Error setting valve {valve}: {e}")
            # Revert checkbox state
            if valve in self._valve_controls:
                self._valve_controls[valve].setChecked(not state)

    async def _on_flow_changed(self, flow: str, value: float) -> None:
        """Handle flow setpoint change."""
        try:
            await self._ui_manager.send_update(
                "hardware/flow/set",
                {
                    "flow": flow,
                    "value": value
                }
            )
        except Exception as e:
            logger.error(f"Error setting {flow} flow: {e}")
            # Revert value
            if flow in self._flow_controls:
                self._flow_controls[flow].setValue(self._flow_values.get(flow, 0.0))

    async def _on_feeder_changed(self, value: float) -> None:
        """Handle feeder speed change."""
        try:
            await self._ui_manager.send_update(
                "hardware/feeder/set",
                {"speed": value}
            )
        except Exception as e:
            logger.error(f"Error setting feeder speed: {e}")
            # Revert value
            if self._feeder_speed_control:
                self._feeder_speed_control.setValue(self._feeder_speed)