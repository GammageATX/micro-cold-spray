"""Motion control service."""

from typing import Dict
from loguru import logger

from ...base import ConfigurableService
from ...base.exceptions import HardwareError, ValidationError
from ..clients import PLCClient


class MotionService(ConfigurableService):
    """Service for motion system control."""

    def __init__(self, plc_client: PLCClient):
        """Initialize motion service.
        
        Args:
            plc_client: PLC client for hardware communication
        """
        super().__init__(service_name="motion")
        self._plc = plc_client

    async def move_axis(self, axis: str, position: float, velocity: float) -> None:
        """Execute single axis move.
        
        Args:
            axis: Axis to move (x, y, z)
            position: Target position in mm
            velocity: Move velocity in mm/s
            
        Raises:
            HardwareError: If move fails
            ValidationError: If parameters invalid
        """
        if axis not in ['x', 'y', 'z']:
            raise ValidationError(
                f"Invalid axis: {axis}",
                {"axis": axis, "valid_axes": ['x', 'y', 'z']}
            )
            
        # Get limits from hardware config
        if not -1000 <= position <= 1000:
            raise ValidationError(
                "Position must be between -1000 and 1000 mm",
                {"axis": axis, "position": position, "limits": (-1000, 1000)}
            )
            
        if not 0 <= velocity <= 100:
            raise ValidationError(
                "Velocity must be between 0 and 100 mm/s",
                {"axis": axis, "velocity": velocity, "limits": (0, 100)}
            )
            
        try:
            axis_num = {'x': '1', 'y': '2', 'z': '3'}[axis]
            
            # Set velocity and acceleration
            await self._plc.write_tag(f"{axis.upper()}Axis.Velocity", velocity)
            await self._plc.write_tag(f"{axis.upper()}Axis.Accel", 100)  # Fixed accel
            await self._plc.write_tag(f"{axis.upper()}Axis.Decel", 100)  # Fixed decel
            
            # Set target position and trigger move
            await self._plc.write_tag(f"AMC.Ax{axis_num}Position", position)
            await self._plc.write_tag(f"Move{axis.upper()}", True)
            
            logger.info(f"Started {axis}-axis move to {position} mm")
            
        except Exception as e:
            raise HardwareError(
                f"Failed to move {axis} axis",
                "motion",
                {
                    "axis": axis,
                    "position": position,
                    "velocity": velocity,
                    "error": str(e)
                }
            )

    async def move_xy(self, x_pos: float, y_pos: float, velocity: float) -> None:
        """Execute coordinated XY move.
        
        Args:
            x_pos: X target position in mm
            y_pos: Y target position in mm
            velocity: Move velocity in mm/s
            
        Raises:
            HardwareError: If move fails
            ValidationError: If parameters invalid
        """
        if not -1000 <= x_pos <= 1000:
            raise ValidationError(
                "X position must be between -1000 and 1000 mm",
                {"axis": "x", "position": x_pos, "limits": (-1000, 1000)}
            )
            
        if not -1000 <= y_pos <= 1000:
            raise ValidationError(
                "Y position must be between -1000 and 1000 mm",
                {"axis": "y", "position": y_pos, "limits": (-1000, 1000)}
            )
            
        if not 0 <= velocity <= 100:
            raise ValidationError(
                "Velocity must be between 0 and 100 mm/s",
                {"velocity": velocity, "limits": (0, 100)}
            )
            
        try:
            # Set XY move parameters
            await self._plc.write_tag("XYMove.XPosition", x_pos)
            await self._plc.write_tag("XYMove.YPosition", y_pos)
            await self._plc.write_tag("XYMove.LINVelocity", velocity)
            await self._plc.write_tag("XYMove.LINRamps", 0.5)  # Fixed ramp time
            
            # Trigger coordinated move
            await self._plc.write_tag("MoveXY", True)
            logger.info(f"Started XY move to ({x_pos}, {y_pos}) mm")
            
        except Exception as e:
            raise HardwareError(
                "Failed to execute XY move",
                "motion",
                {
                    "x_position": x_pos,
                    "y_position": y_pos,
                    "velocity": velocity,
                    "error": str(e)
                }
            )

    async def get_status(self) -> Dict[str, float]:
        """Get current motion status.
        
        Returns:
            Motion system status
            
        Raises:
            HardwareError: If status read fails
        """
        try:
            status = {
                'position': {
                    'x': await self._plc.read_tag("AMC.Ax1Position"),
                    'y': await self._plc.read_tag("AMC.Ax2Position"),
                    'z': await self._plc.read_tag("AMC.Ax3Position")
                },
                'moving': {
                    'x': await self._plc.read_tag("XAxis.InProgress"),
                    'y': await self._plc.read_tag("YAxis.InProgress"),
                    'z': await self._plc.read_tag("ZAxis.InProgress")
                },
                'complete': {
                    'x': await self._plc.read_tag("XAxis.Complete"),
                    'y': await self._plc.read_tag("YAxis.Complete"),
                    'z': await self._plc.read_tag("ZAxis.Complete")
                },
                'status': {
                    'x': await self._plc.read_tag("AMC.Ax1AxisStatus"),
                    'y': await self._plc.read_tag("AMC.Ax2AxisStatus"),
                    'z': await self._plc.read_tag("AMC.Ax3AxisStatus")
                }
            }
            return status
            
        except Exception as e:
            raise HardwareError(
                "Failed to get motion status",
                "motion",
                {"error": str(e)}
            )
