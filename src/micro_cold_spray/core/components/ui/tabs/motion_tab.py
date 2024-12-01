"""Motion control tab for manual motion and position management."""
import asyncio
import logging
from typing import Any, Dict, Protocol, runtime_checkable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QMessageBox, QSplitter, QVBoxLayout

from ..managers.ui_update_manager import UIUpdateManager
from ..widgets.base_widget import BaseWidget
from ..widgets.motion.chamber_view import ChamberView
from ..widgets.motion.jog_control import JogControl
from ..widgets.motion.position_table import PositionTable

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
            self._motion_limits = hardware_config['hardware']['motion']['limits']
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
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_frame.setFrameShadow(QFrame.Shadow.Raised)
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
                await self._update_simulated_position(new_position)
                self._simulated_moving = True

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

            await self._ui_manager.register_widget(
                self._widget_id,
                ["motion/error"],
                self
            )

        except Exception as e:
            logger.error(f"Error handling jog command: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {"error": f"Motion error: {str(e)}"}
            )

    async def _handle_motion_error(self, error_data: Dict[str, Any]) -> None:
        """Handle motion error messages."""
        try:
            error_msg = error_data.get("error", "Unknown motion error")
            # Show error in UI
            await self._ui_manager.send_update(
                "system/error",
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

                # If connection state changed, update position source
                if was_connected != self._connected:
                    if self._connected:
                        # Switch to real position updates
                        logger.debug("Switching to hardware position updates")
                    else:
                        # Switch to simulation
                        logger.debug("Switching to simulated position updates")
                        # Initialize simulation position
                        await self._update_simulated_position(self._simulated_position)

            elif "motion.position" in data and self._connected:
                # Only use hardware position updates when connected
                position = data["motion.position"]
                await self._update_position_displays(position)

            elif "hardware_status" in data:
                # Handle hardware status updates
                status = data.get("hardware_status", {})
                self._connected = status.get("plc_connected", False)

            elif "tag_update" in data:
                # Handle tag updates
                for tag, value in data.items():
                    if tag.startswith("motion.position"):
                        if self._connected:
                            await self._update_position_displays(value)

        except Exception as e:
            logger.error(f"Error handling UI update in MotionTab: {e}")
            await self.send_update("system.error", f"Motion tab error: {str(e)}")

    async def _update_simulated_position(
            self, position: Dict[str, float]) -> None:
        """Update simulated position when in disconnected mode."""
        try:
            self._simulated_position = position
            await self._update_position_displays(position)
            # Also update the position table
            if self._position_table:
                self._position_table._current_position = position
        except Exception as e:
            logger.error(f"Error updating simulated position: {e}")

    async def _update_position_displays(
            self, position: Dict[str, float]) -> None:
        """Update all position displays."""
        try:
            # Update chamber view
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
                self._position_table._current_position = position

        except Exception as e:
            logger.error(f"Error updating position displays: {e}")

    async def cleanup(self) -> None:
        """Clean up motion tab and child widgets."""
        try:
            # Clean up child widgets first
            if self._chamber_view is not None:
                if (
                        hasattr(self._chamber_view, 'cleanup')
                        and asyncio.iscoroutinefunction(self._chamber_view.cleanup)
                ):
                    try:
                        await self._chamber_view.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up chamber view: {e}")
                elif hasattr(self._chamber_view, 'cleanup'):
                    try:
                        # Call sync cleanup directly
                        self._chamber_view.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up chamber view: {e}")

            if self._jog_control is not None:
                if (
                        hasattr(self._jog_control, 'cleanup')
                        and asyncio.iscoroutinefunction(self._jog_control.cleanup)
                ):
                    try:
                        await self._jog_control.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up jog control: {e}")
                elif hasattr(self._jog_control, 'cleanup'):
                    try:
                        # Call sync cleanup directly
                        await self._jog_control.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up jog control: {e}")

            if self._position_table is not None:
                if (
                        hasattr(self._position_table, 'cleanup')
                        and asyncio.iscoroutinefunction(self._position_table.cleanup)
                ):
                    try:
                        await self._position_table.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up position table: {e}")
                elif hasattr(self._position_table, 'cleanup'):
                    try:
                        # Call sync cleanup directly
                        await self._position_table.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up position table: {e}")

            # Then clean up self
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during motion tab cleanup: {e}")

    def _validate_position(self, axis: str, position: float) -> bool:
        """Validate position against axis limits."""
        try:
            axis_limits = self._motion_limits.get(axis.lower(), {})
            min_limit = axis_limits.get('min', float('-inf'))
            max_limit = axis_limits.get('max', float('inf'))

            if position < min_limit:
                logger.warning(
                    f"{axis} position {position} below minimum limit {min_limit}")
                return False
            if position > max_limit:
                logger.warning(
                    f"{axis} position {position} above maximum limit {max_limit}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating position: {e}")
            return False
