"""Motion control tab for manual motion and position management."""
import asyncio
from typing import Any, Dict, Protocol, runtime_checkable

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QMessageBox, QSplitter, QVBoxLayout

from ..managers.ui_update_manager import UIUpdateManager
from ..widgets.base_widget import BaseWidget
from ..widgets.motion.chamber_view import ChamberView
from ..widgets.motion.jog_control import JogControl
from ..widgets.motion.position_table import PositionTable


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
        parent=None
    ):
        super().__init__(
            widget_id="tab_motion",
            ui_manager=ui_manager,
            update_tags=[
                "motion.position",
                "motion.state",
                "motion.error",
                "system.state",
                "system.connection",
                "hardware_status",
                "tag_update"
            ],
            parent=parent
        )

        # Track simulation state
        self._simulated_position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self._connected = False
        self._simulated_moving = False

        # Store widget references
        self._chamber_view = None
        self._jog_control = None
        self._position_table = None

        # Initialize motion limits
        self._motion_limits = {}  # Initialize empty
        asyncio.create_task(self._load_motion_limits())  # Load async

        self._init_ui()
        logger.info("Motion tab initialized")

    async def _load_motion_limits(self):
        """Load motion limits from config."""
        try:
            hardware_config = await self._ui_manager._config_manager.get_config('hardware')
            limits = hardware_config.get('hardware', {})
            limits = limits.get('motion', {})
            self._motion_limits = limits.get('limits', {})
            logger.debug(f"Loaded motion limits: {self._motion_limits}")
        except Exception as e:
            logger.error(f"Error loading motion limits: {e}")

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
        self._position_table = PositionTable(self._ui_manager)
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
                "motion.position",
                {
                    "position": self._simulated_position,
                    "simulated": True,
                    "timestamp": None
                }
            )

            logger.debug(f"Updated simulated position: {self._simulated_position}")

        except Exception as e:
            logger.error(f"Error updating simulated position: {e}")

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

                # Validate against limits
                axis_limits = self._motion_limits.get(axis.lower(), {})
                min_limit = axis_limits.get('min', float('-inf'))
                max_limit = axis_limits.get('max', float('inf'))

                new_pos = new_position[axis.lower()] + increment

                # Check if move would exceed limits
                if new_pos < min_limit:
                    logger.warning(
                        f"{axis} move would exceed minimum limit of {min_limit}")
                    return
                if new_pos > max_limit:
                    logger.warning(
                        f"{axis} move would exceed maximum limit of {max_limit}")
                    return

                # Apply validated move
                new_position[axis.lower()] = new_pos
                self._simulated_position = new_position

                # Update chamber view first
                if self._chamber_view:
                    self._chamber_view.update_position(
                        new_position['x'],
                        new_position['y'],
                        new_position['z']
                    )

                # Update jog control display
                if self._jog_control:
                    self._jog_control._update_position_display(new_position)

                # Update position table
                if self._position_table:
                    await self._position_table.update_position(new_position)

                # Send position update through UI manager
                await self._ui_manager.send_update(
                    "motion.position",
                    {
                        "position": new_position,
                        "simulated": True,
                        "timestamp": None
                    }
                )

                logger.debug(f"Updated position to: {new_position}")

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
                "system.error",
                {"error": f"Motion error: {str(e)}"}
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
                    {"immediate": True}
                )
        except Exception as e:
            logger.error(f"Error handling stop command: {e}")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates from UIUpdateManager."""
        try:
            if "system.connection" in data:
                was_connected = self._connected
                self._connected = data.get("connected", False)
                if was_connected != self._connected:
                    # Reset simulated position when connection state changes
                    if not self._connected:
                        self._simulated_position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
                        # Update all widgets with initial position
                        if self._chamber_view:
                            self._chamber_view.update_position(0.0, 0.0, 0.0)
                        if self._jog_control:
                            self._jog_control._update_position_display(self._simulated_position)
                        if self._position_table:
                            await self._position_table.update_position(self._simulated_position)

            elif "motion.position" in data:
                position_data = data.get("motion.position", {})
                if isinstance(position_data, dict):
                    if "position" in position_data:
                        position = position_data["position"]
                    else:
                        position = position_data

                    # Update all widgets with new position
                    if self._chamber_view:
                        self._chamber_view.update_position(
                            position.get('x', 0.0),
                            position.get('y', 0.0),
                            position.get('z', 0.0)
                        )
                    if self._jog_control:
                        self._jog_control._update_position_display(position)
                    if self._position_table:
                        await self._position_table.update_position(position)

                    # Store position
                    self._simulated_position = position.copy()

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    async def _handle_motion_error(self, error_data: Dict[str, Any]) -> None:
        """Handle motion error messages."""
        try:
            error_msg = error_data.get("error", "Unknown motion error")
            # Show error in UI
            await self._ui_manager.send_update(
                "system.error",
                {"error": error_msg}
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
