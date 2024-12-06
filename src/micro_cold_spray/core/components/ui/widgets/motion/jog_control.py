"""Motion jog control widget for manual motion control."""
import asyncio
import logging
from typing import Dict, Optional, Protocol, runtime_checkable, Any
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


@runtime_checkable
class MotionTabProtocol(Protocol):
    """Protocol for motion tab interface."""

    async def handle_jog_command(
        self,
        axis: str,
        direction: int,
        speed: float,
        step_size: float
    ) -> None:
        """Handle jog command."""
        pass

    async def handle_stop_command(self) -> None:
        """Handle stop command."""
        pass


class JogControl(BaseWidget):
    """Jog control widget for manual motion control."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None,
        motion_tab: Optional[MotionTabProtocol] = None
    ):
        super().__init__(
            widget_id="control_motion_jog",
            ui_manager=ui_manager,
            update_tags=[
                "motion.position",
                "motion.state",
                "system.connection",
                "hardware.stage"
            ],
            parent=parent
        )

        # Store protocol implementation
        self._motion_tab = motion_tab
        if not motion_tab:
            logger.warning("No motion tab protocol implementation available")

        # Initialize current position and stage limits
        self._current_position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self._stage_limits = {
            'x': {'min': 0.0, 'max': 200.0},
            'y': {'min': 0.0, 'max': 200.0},
            'z': {'min': 0.0, 'max': 40.0}
        }

        # Store button handlers for cleanup
        self._button_handlers = []

        self._init_ui()

    async def _handle_jog_button(self, axis: str, direction: int) -> None:
        """Handle jog button press."""
        try:
            if self._motion_tab:
                # Get step size and speed
                step_size = float(self.step_combo.currentText())
                speed = self._get_current_speed()

                # Log the move attempt
                logger.debug(
                    f"Jog {axis}{'+' if direction > 0 else '-'}: "
                    f"step={step_size}, direction={direction}, speed={speed}"
                )

                # Let motion tab handle validation and execution
                await self._motion_tab.handle_jog_command(
                    axis=axis,
                    direction=direction,
                    speed=speed,
                    step_size=step_size
                )
        except Exception as e:
            logger.error(f"Error handling jog command: {e}")

    async def _handle_stop_button(self) -> None:
        """Handle stop button press."""
        try:
            if self._motion_tab:
                await self._motion_tab.handle_stop_command()
        except Exception as e:
            logger.error(f"Error handling stop command: {e}")

    def _init_ui(self) -> None:
        """Setup the widget UI."""
        layout = QVBoxLayout()

        # Speed control
        speed_group = QGroupBox("Jog Speed")
        speed_layout = QHBoxLayout()
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 1000.0)
        self.speed_spin.setValue(10.0)
        self.speed_spin.setSuffix(" mm/s")
        speed_layout.addWidget(self.speed_spin)
        speed_group.setLayout(speed_layout)
        layout.addWidget(speed_group)

        # Step size control
        step_group = QGroupBox("Step Size")
        step_layout = QHBoxLayout()
        self.step_combo = QComboBox()
        self.step_combo.addItems(["0.1", "1.0", "10.0", "100.0"])
        self.step_combo.setCurrentText("1.0")
        step_layout.addWidget(self.step_combo)
        step_layout.addWidget(QLabel("mm"))
        step_group.setLayout(step_layout)
        layout.addWidget(step_group)

        # Jog buttons
        jog_group = QGroupBox("Jog Control")
        jog_layout = QGridLayout()

        # Z axis controls (up/down)
        self.z_up_btn = QPushButton("Z+")
        self.z_down_btn = QPushButton("Z-")
        jog_layout.addWidget(self.z_up_btn, 0, 1)
        jog_layout.addWidget(self.z_down_btn, 2, 1)

        # X/Y axis controls
        self.y_down_btn = QPushButton("Y+")
        self.y_up_btn = QPushButton("Y-")
        self.x_left_btn = QPushButton("X-")
        self.x_right_btn = QPushButton("X+")

        jog_layout.addWidget(self.y_up_btn, 0, 2)
        jog_layout.addWidget(self.y_down_btn, 2, 2)
        jog_layout.addWidget(self.x_left_btn, 1, 1)
        jog_layout.addWidget(self.x_right_btn, 1, 3)

        # Connect jog buttons with proper async handling
        for btn, (axis, direction) in [
            (self.x_left_btn, ('x', -1)),
            (self.x_right_btn, ('x', 1)),
            (self.y_up_btn, ('y', -1)),
            (self.y_down_btn, ('y', 1)),
            (self.z_up_btn, ('z', 1)),
            (self.z_down_btn, ('z', -1))
        ]:
            # Create press and release handlers using proper function definitions
            def make_press_handler(a=axis, d=direction):
                def handler():
                    return asyncio.create_task(self._handle_jog_button(a, d))
                return handler

            def make_release_handler(a=axis):
                def handler():
                    return asyncio.create_task(self._handle_stop_button())
                return handler

            # Create handler instances
            press_handler = make_press_handler()
            release_handler = make_release_handler()

            # Connect handlers
            btn.pressed.connect(press_handler)
            btn.released.connect(release_handler)

            # Store handlers for cleanup
            self._button_handlers.append((btn, press_handler, release_handler))

        jog_group.setLayout(jog_layout)
        layout.addWidget(jog_group)

        # Position display
        pos_group = QGroupBox("Current Position")
        pos_layout = QGridLayout()

        self.x_pos_label = QLabel("0.000")
        self.y_pos_label = QLabel("0.000")
        self.z_pos_label = QLabel("0.000")

        pos_layout.addWidget(QLabel("X:"), 0, 0)
        pos_layout.addWidget(self.x_pos_label, 0, 1)
        pos_layout.addWidget(QLabel("mm"), 0, 2)

        pos_layout.addWidget(QLabel("Y:"), 1, 0)
        pos_layout.addWidget(self.y_pos_label, 1, 1)
        pos_layout.addWidget(QLabel("mm"), 1, 2)

        pos_layout.addWidget(QLabel("Z:"), 2, 0)
        pos_layout.addWidget(self.z_pos_label, 2, 1)
        pos_layout.addWidget(QLabel("mm"), 2, 2)

        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)

        self.setLayout(layout)

    def _get_current_speed(self) -> float:
        """Get the current jog speed."""
        return self.speed_spin.value()

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Disconnect all button handlers
            for btn, press_handler, release_handler in self._button_handlers:
                try:
                    btn.pressed.disconnect(press_handler)
                    btn.released.disconnect(release_handler)
                except Exception:
                    pass  # Ignore disconnection errors
            self._button_handlers.clear()

            # Call parent cleanup
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during jog control cleanup: {e}")

    def _update_position_display(self, position: Dict[str, float]) -> None:
        """Update position display labels."""
        try:
            self.x_pos_label.setText(f"{position.get('x', 0.0):.3f}")
            self.y_pos_label.setText(f"{position.get('y', 0.0):.3f}")
            self.z_pos_label.setText(f"{position.get('z', 0.0):.3f}")
        except Exception as e:
            logger.error(f"Error updating position display: {e}")

    def _validate_position(self, axis: str, value: float) -> bool:
        """Validate position is within stage limits."""
        min_limit = self._stage_limits[axis]['min']
        max_limit = self._stage_limits[axis]['max']
        if value < min_limit:
            logger.error(f"{axis} position {value} below min {min_limit}")
            return False
        if value > max_limit:
            logger.error(f"{axis} position {value} above max {max_limit}")
            return False
        return True

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "motion.position" in data:
                position_data = data.get("motion.position", {})
                if isinstance(position_data, dict):
                    # Handle both direct position dict and nested format
                    if "data" in position_data and "position" in position_data["data"]:
                        pos = position_data["data"]["position"]
                    elif "position" in position_data:
                        pos = position_data["position"]
                    else:
                        pos = position_data

                    self._update_position_display(pos)

            elif "hardware.stage" in data:
                # Update stage limits if they change
                if 'limits' in data["hardware.stage"]:
                    self._stage_limits = data["hardware.stage"]["limits"]

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    def _update_control_state(self, connected: bool) -> None:
        """Update control state based on connection status."""
        try:
            # In disconnected mode, we still allow jog controls for simulation
            self.speed_spin.setEnabled(True)
            self.step_combo.setEnabled(True)

            # Enable all jog buttons
            for btn in [
                self.x_left_btn, self.x_right_btn,
                self.y_up_btn, self.y_down_btn,
                self.z_up_btn, self.z_down_btn
            ]:
                btn.setEnabled(True)

        except Exception as e:
            logger.error(f"Error updating control state: {e}")

    def _is_move_valid(self, axis: str, direction: int, step_size: float) -> bool:
        """Check if the proposed move is within stage bounds."""
        try:
            # Get current position
            current_pos = self._current_position.get(axis, 0.0)

            # Calculate new position
            new_pos = current_pos + (direction * step_size)

            # Check if move would exceed limits
            if new_pos < self._stage_limits[axis]['min'] or new_pos > self._stage_limits[axis]['max']:
                logger.warning(
                    f"Move would exceed {axis} axis limits: {new_pos} not in "
                    f"[{self._stage_limits[axis]['min']}, {self._stage_limits[axis]['max']}]"
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating move: {e}")
            return False
