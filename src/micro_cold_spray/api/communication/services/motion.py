"""Motion control service."""

from loguru import logger

from ...base import BaseService
from ..exceptions import HardwareError
from ..clients import PLCClient
from ..models.motion import MotionStatus


class MotionService(BaseService):
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
            ValueError: If parameters invalid
        """
        if axis not in ['x', 'y', 'z']:
            raise ValueError(f"Invalid axis: {axis}")
            
        if not -1000 <= position <= 1000:
            raise ValueError("Position must be between -1000 and 1000 mm")
            
        if not 0 <= velocity <= 100:
            raise ValueError("Velocity must be between 0 and 100 mm/s")
            
        try:
            # Write motion parameters
            await self._plc.write_tag(f"motion.{axis}.target", position)
            await self._plc.write_tag(f"motion.{axis}.velocity", velocity)
            
            # Trigger move
            await self._plc.write_tag(f"motion.{axis}.start", True)
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
            ValueError: If parameters invalid
        """
        if not -1000 <= x_pos <= 1000:
            raise ValueError("X position must be between -1000 and 1000 mm")
            
        if not -1000 <= y_pos <= 1000:
            raise ValueError("Y position must be between -1000 and 1000 mm")
            
        if not 0 <= velocity <= 100:
            raise ValueError("Velocity must be between 0 and 100 mm/s")
            
        try:
            # Write motion parameters
            await self._plc.write_tag("motion.x.target", x_pos)
            await self._plc.write_tag("motion.y.target", y_pos)
            await self._plc.write_tag("motion.xy.velocity", velocity)
            
            # Trigger coordinated move
            await self._plc.write_tag("motion.xy.start", True)
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

    async def get_status(self) -> MotionStatus:
        """Get current motion status.
        
        Returns:
            Motion system status
            
        Raises:
            HardwareError: If status read fails
        """
        try:
            # Read axis positions
            x_pos = await self._plc.read_tag("motion.x.position")
            y_pos = await self._plc.read_tag("motion.y.position")
            z_pos = await self._plc.read_tag("motion.z.position")
            
            # Read axis states
            x_moving = await self._plc.read_tag("motion.x.moving")
            y_moving = await self._plc.read_tag("motion.y.moving")
            z_moving = await self._plc.read_tag("motion.z.moving")
            
            # Read error states
            x_error = await self._plc.read_tag("motion.x.error")
            y_error = await self._plc.read_tag("motion.y.error")
            z_error = await self._plc.read_tag("motion.z.error")
            
            return MotionStatus(
                x_position=x_pos,
                y_position=y_pos,
                z_position=z_pos,
                x_moving=x_moving,
                y_moving=y_moving,
                z_moving=z_moving,
                x_error=x_error,
                y_error=y_error,
                z_error=z_error
            )
            
        except Exception as e:
            raise HardwareError(
                "Failed to get motion status",
                "motion",
                {"error": str(e)}
            )
