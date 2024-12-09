"""Motion control tab for manual motion and position management."""
from typing import Any, Dict, Protocol, runtime_checkable

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QMessageBox, QSplitter, QVBoxLayout

from ..managers.ui_update_manager import UIUpdateManager
from ..widgets.base_widget import BaseWidget
from ..widgets.motion.chamber_view import ChamberView
from ..widgets.motion.jog_control import JogControl
from ..widgets.motion.position_table import PositionTable
from ...infrastructure.messaging.message_broker import MessageBroker


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

    async def handle_stop_command(self) -> None:
        """Handle stop command."""


class MotionTab(BaseWidget):
    """Tab for motion control and visualization."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        message_broker: MessageBroker,
        parent=None
    ):
        super().__init__(
            widget_id="tab_motion",
            ui_manager=ui_manager,
            update_tags=[
                "motion/position",
                "motion/state",
                "motion/error",
                "system/state",
                "system/connection",
                "hardware/status",
                "hardware/stage",
                "system/error"
            ],
            parent=parent
        )

        # Store dependencies
        self._message_broker = message_broker

        # Track simulation state
        self._simulated_position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self._connected = False
        self._simulated_moving = False

        # Store widget references
        self._chamber_view = None
        self._jog_control = None
        self._position_table = None

        # Initialize motion limits
        self._motion_limits = {
            'x': {'min': 0.0, 'max': 200.0},
            'y': {'min': 0.0, 'max': 200.0},
            'z': {'min': 0.0, 'max': 40.0}
        }

        self._init_ui()
        logger.info("Motion tab initialized")

    def _init_ui(self):
        """Initialize the motion tab UI."""
        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 5, 10, 10)
        main_layout.setSpacing(5)

        # Add header
        header = QLabel("Motion Control")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.setMaximumHeight(25)
        main_layout.addWidget(header)

        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Chamber view
        chamber_frame = QFrame()
        chamber_frame.setFrameShape(QFrame.Shape.StyledPanel)
        chamber_frame.setFrameShadow(QFrame.Shadow.Raised)
        chamber_layout = QVBoxLayout()

        # Add chamber view
        self._chamber_view = ChamberView(self._ui_manager)
        chamber_layout.addWidget(self._chamber_view)

        chamber_frame.setLayout(chamber_layout)
        splitter.addWidget(chamber_frame)

        # Right side - Controls and positions
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.Panel)
        controls_frame.setFrameShadow(QFrame.Shadow.Sunken)
        controls_layout = QVBoxLayout()

        # Add jog control with explicit parent and protocol reference
        self._jog_control = JogControl(
            ui_manager=self._ui_manager,
            parent=self,  # Pass self as parent
            motion_tab=self  # Pass self as motion_tab protocol implementation
        )
        controls_layout.addWidget(self._jog_control)

        # Add position table
        self._position_table = PositionTable(
            ui_manager=self._ui_manager,
            motion_tab=self,  # Pass self reference
            parent=self
        )
        controls_layout.addWidget(self._position_table)

        controls_frame.setLayout(controls_layout)
        splitter.addWidget(controls_frame)

        # Set initial splitter sizes (60% chamber view, 40% controls)
        splitter.setSizes([600, 400])

        # Add splitter to main layout
        main_layout.addWidget(splitter)

        self.setLayout(main_layout)

    async def _update_simulated_position(self, new_position: Dict[str, float]) -> None:
        """Update simulated position and notify widgets."""
        try:
            self._simulated_position = new_position

            # Send position update through UI manager
            await self._ui_manager.send_update(
                "motion/position",
                {
                    "position": self._simulated_position,
                    "simulated": True,
                    "timestamp": None
                }
            )

            logger.debug(f"Updated simulated position: {self._simulated_position}")

        except Exception as e:
            logger.error(f"Error updating simulated position: {e}")

    def _validate_position(self, position: Dict[str, float]) -> bool:
        """Validate position against motion limits."""
        try:
            for axis, value in position.items():
                axis_limits = self._motion_limits.get(axis.lower(), {})
                min_limit = axis_limits.get('min', 0.0)
                max_limit = axis_limits.get('max', float('inf'))

                if value < min_limit or value > max_limit:
                    logger.warning(
                        f"{axis} position {value} outside limits "
                        f"[{min_limit}, {max_limit}]"
                    )
                    return False
            return True
        except Exception as e:
            logger.error(f"Error validating position: {e}")
            return False

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates from UIUpdateManager."""
        try:
            if "system/connection" in data:
                was_connected = self._connected
                self._connected = data.get("connected", False)
                if was_connected != self._connected:
                    # Reset simulated position when connection state changes
                    if not self._connected:
                        self._simulated_position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
                        # Update all widgets with initial position
                        await self._update_all_displays(self._simulated_position)

            elif "motion/position" in data:
                position_data = data.get("motion/position", {})
                if isinstance(position_data, dict):
                    # Skip updates from position table to prevent loops
                    if position_data.get("source") == "position_table":
                        return

                    if "position" in position_data:
                        position = position_data["position"]
                    else:
                        position = position_data

                    # Only update if position is valid
                    if self._validate_position(position):
                        # Update all widgets with validated position
                        await self._update_all_displays(position)
                        # Store position
                        self._simulated_position = position.copy()
                    else:
                        logger.warning("Received invalid position update - ignoring")

            elif "hardware/stage" in data:
                stage_data = data.get("hardware/stage", {})
                if isinstance(stage_data, dict):
                    dimensions = stage_data.get("dimensions", {})
                    if dimensions:
                        self._motion_limits = {
                            'x': {'min': 0.0, 'max': dimensions.get('x', 200.0)},
                            'y': {'min': 0.0, 'max': dimensions.get('y', 200.0)},
                            'z': {'min': 0.0, 'max': dimensions.get('z', 40.0)}
                        }

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "motion_tab",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _update_all_displays(self, position: Dict[str, float]) -> None:
        """Update all displays with a validated position."""
        try:
            # Update chamber view first
            if self._chamber_view:
                self._chamber_view.update_position(
                    position['x'],
                    position['y'],
                    position['z']
                )

            # Update jog control display
            if self._jog_control:
                self._jog_control._update_position_display(position)

            # Update position table
            if self._position_table:
                await self._position_table.update_position(position)

        except Exception as e:
            logger.error(f"Error updating displays: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "motion_tab",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def handle_jog_command(
            self,
            axis: str,
            direction: int,
            speed: float,
            step_size: float) -> None:
        """Handle jog command from jog control."""
        try:
            if not self._connected:
                # Calculate new position
                new_position = self._simulated_position.copy()
                increment = direction * step_size
                new_position[axis.lower()] = new_position[axis.lower()] + increment

                # Validate entire position
                if self._validate_position(new_position):
                    # Move is valid, update position
                    self._simulated_position = new_position
                    # Update all displays with the valid position
                    await self._update_all_displays(new_position)
                    logger.debug(f"Updated position to: {new_position}")
                else:
                    logger.warning(f"Invalid move rejected: {new_position}")

            else:
                # Send real motion command with validation
                await self._ui_manager.send_update(
                    "motion/command/jog",
                    {
                        "axis": axis,
                        "direction": direction,
                        "speed": speed,
                        "distance": step_size
                    }
                )

        except Exception as e:
            logger.error(f"Error handling jog command: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "motion_tab",
                    "message": f"Motion error: {str(e)}",
                    "level": "error"
                }
            )

    async def handle_stop_command(self) -> None:
        """Handle stop command from jog control."""
        try:
            if not self._connected:
                # Stop simulated motion
                self._simulated_moving = False
            else:
                # Send real stop command
                await self._ui_manager.send_update(
                    "motion/command/stop",
                    {
                        "immediate": True
                    }
                )
        except Exception as e:
            logger.error(f"Error handling stop command: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "motion_tab",
                    "message": f"Stop error: {str(e)}",
                    "level": "error"
                }
            )

    async def _handle_motion_error(self, error_data: Dict[str, Any]) -> None:
        """Handle motion error messages."""
        try:
            error_msg = error_data.get("error", "Unknown motion error")
            # Show error in UI
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "motion_tab",
                    "message": error_msg,
                    "level": "error"
                }
            )
            # Could also show in a popup or status bar
            QMessageBox.warning(
                self,
                "Motion Error",
                error_msg
            )
        except Exception as e:
            logger.error(f"Error handling motion error: {e}")

    async def cleanup(self) -> None:
        """Clean up motion tab and child widgets."""
        try:
            # Clean up child widgets first
            if self._chamber_view is not None:
                await self._chamber_view.cleanup()
            if self._jog_control is not None:
                await self._jog_control.cleanup()
            if self._position_table is not None:
                await self._position_table.cleanup()

            # Then clean up self
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during motion tab cleanup: {e}")

    async def handle_move_command(self, position: Dict[str, float]) -> None:
        """Handle move command to absolute position."""
        try:
            # Validate position against stage limits
            if not self._validate_position(position):
                logger.warning(f"Move to position {position} rejected - outside limits")
                return

            if not self._connected:
                # In disconnected mode, update simulated position
                if self._validate_position(position):
                    # Move is valid, update position
                    self._simulated_position = position.copy()
                    # Update all displays with the valid position
                    await self._update_all_displays(position)
                    logger.debug(f"Updated position to: {position}")
            else:
                # Send real motion command with validation
                await self._ui_manager.send_update(
                    "motion/command/move",
                    {
                        "position": position,
                        "speed": 10.0,  # Default speed
                        "simulated": False
                    }
                )

        except Exception as e:
            logger.error(f"Error handling move command: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "motion_tab",
                    "message": f"Motion error: {str(e)}",
                    "level": "error"
                }
            )
