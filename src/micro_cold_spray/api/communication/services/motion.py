"""Motion service implementation."""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import status as http_status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.services.tag_cache import TagCacheService
from micro_cold_spray.api.communication.models.motion import Position, SystemStatus, AxisStatus


class MotionService:
    """Service for motion control."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize motion service.
        
        Args:
            config: Service configuration
        """
        self._service_name = "motion"
        self._version = "1.0.0"
        self._config = config
        self._tag_cache: Optional[TagCacheService] = None
        self._is_running = False
        self._start_time = None
        logger.info("MotionService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def initialize(self) -> None:
        """Initialize motion service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=http_status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Initialize tag cache
            if not self._tag_cache:
                logger.error("Tag cache service not initialized")
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Tag cache service not initialized"
                )

            # Wait for tag cache service to be ready
            if not self._tag_cache.is_running:
                logger.error("Tag cache service not running")
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Tag cache service not running"
                )

            logger.info("Motion service initialized")

        except Exception as e:
            error_msg = f"Failed to initialize motion service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start motion service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=http_status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Initialize if needed
            if not self._tag_cache or not self._tag_cache.is_running:
                await self.initialize()

            self._start_time = datetime.now()
            self._is_running = True
            logger.info("Motion service started")

        except Exception as e:
            error_msg = f"Failed to start motion service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop motion service."""
        try:
            if not self.is_running:
                return

            self._is_running = False
            self._start_time = None
            logger.info("Motion service stopped")

        except Exception as e:
            error_msg = f"Failed to stop motion service: {str(e)}"
            logger.error(error_msg)
            # Don't raise during shutdown

    def set_tag_cache(self, tag_cache: TagCacheService) -> None:
        """Set tag cache service.
        
        Args:
            tag_cache: Tag cache service instance
        """
        self._tag_cache = tag_cache

    async def get_position(self) -> Position:
        """Get current position.
        
        Returns:
            Current position
            
        Raises:
            HTTPException: If read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Read position tags from AMC controller
            logger.debug("Reading position tags...")
            x = await self._tag_cache.read_tag("motion.position.x_position")  # AMC.Ax1Position
            logger.debug(f"X position = {x}")
            y = await self._tag_cache.read_tag("motion.position.y_position")  # AMC.Ax2Position
            logger.debug(f"Y position = {y}")
            z = await self._tag_cache.read_tag("motion.position.z_position")  # AMC.Ax3Position
            logger.debug(f"Z position = {z}")

            return Position(x=x, y=y, z=z)

        except Exception as e:
            error_msg = "Failed to get position"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def get_status(self) -> SystemStatus:
        """Get motion system status.
        
        Returns:
            System status
            
        Raises:
            HTTPException: If read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Read motion controller status
            logger.debug("Reading motion controller status...")
            module_ready = await self._tag_cache.read_tag("interlocks.motion_ready")  # AMC.ModuleStatus
            logger.debug(f"Module ready = {module_ready}")
            
            # Read axis status bits
            logger.debug("Reading axis status bits...")
            x_status = await self._tag_cache.read_tag("motion.status.x_axis")  # AMC.Ax1AxisStatus
            logger.debug(f"X status = {x_status} (0x{x_status:04X})")
            y_status = await self._tag_cache.read_tag("motion.status.y_axis")  # AMC.Ax2AxisStatus
            logger.debug(f"Y status = {y_status} (0x{y_status:04X})")
            z_status = await self._tag_cache.read_tag("motion.status.z_axis")  # AMC.Ax3AxisStatus
            logger.debug(f"Z status = {z_status} (0x{z_status:04X})")

            # Parse status bits
            # Bit 4: Initialization Complete
            # Bit 16: Axis Occupied (busy)
            enabled = bool(x_status & (1 << 4) and y_status & (1 << 4) and z_status & (1 << 4))
            logger.debug(f"Enabled = {enabled}")
            busy = bool(x_status & (1 << 16) or y_status & (1 << 16) or z_status & (1 << 16))
            logger.debug(f"Busy = {busy}")
            
            # Bit 7: Stopped at Move Target (homed)
            homed = bool(x_status & (1 << 7) and y_status & (1 << 7) and z_status & (1 << 7))
            logger.debug(f"Homed = {homed}")
            
            # Bits 10-15: Various error conditions
            error = bool(
                x_status & 0xFC00 or  # Bits 10-15
                y_status & 0xFC00 or
                z_status & 0xFC00
            )
            logger.debug(f"Error = {error}")

            return SystemStatus(
                enabled=enabled and module_ready,
                homed=homed,
                error=error,
                busy=busy
            )

        except Exception as e:
            error_msg = "Failed to get status"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def get_axis_status(self, axis: str) -> AxisStatus:
        """Get axis status.
        
        Args:
            axis: Axis name (x, y, z)
            
        Returns:
            Axis status
            
        Raises:
            HTTPException: If read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate axis
            if axis not in ["x", "y", "z"]:
                raise create_error(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid axis: {axis}"
                )

            # Map axis to status tag
            status_tag = f"motion.status.{axis}_axis"  # AMC.Ax[1/2/3]AxisStatus
            axis_status = await self._tag_cache.read_tag(status_tag)

            # Parse status bits
            enabled = bool(axis_status & (1 << 4))  # Bit 4: Initialization Complete
            busy = bool(axis_status & (1 << 16))    # Bit 16: Axis Occupied
            homed = bool(axis_status & (1 << 7))    # Bit 7: Stopped at Move Target
            error = bool(axis_status & 0xFC00)      # Bits 10-15: Error conditions

            return AxisStatus(
                enabled=enabled,
                homed=homed,
                error=error,
                busy=busy
            )

        except Exception as e:
            error_msg = f"Failed to get {axis} axis status"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def move(self, position: Position) -> None:
        """Move to position.
        
        Args:
            position: Target position
            
        Raises:
            HTTPException: If move fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Set XY move parameters
            await self._tag_cache.write_tag("motion.motion_control.coordinated_move.xy_move.parameters.x_position", position.x)
            await self._tag_cache.write_tag("motion.motion_control.coordinated_move.xy_move.parameters.y_position", position.y)
            
            # Trigger XY move
            await self._tag_cache.write_tag("motion.motion_control.coordinated_move.xy_move.trigger", True)
            
            # Set Z position and trigger move
            await self._tag_cache.write_tag("motion.motion_control.relative_move.z_move.parameters.velocity", position.z)
            await self._tag_cache.write_tag("motion.motion_control.relative_move.z_move.trigger", True)

        except Exception as e:
            error_msg = "Failed to move"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def jog(self, axis: str, distance: float) -> None:
        """Jog axis by distance.
        
        Args:
            axis: Axis to jog (x, y, z)
            distance: Jog distance
            
        Raises:
            HTTPException: If jog fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate axis
            if axis not in ["x", "y", "z"]:
                raise create_error(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid axis: {axis}"
                )

            # Set velocity and trigger move
            move_tag = f"motion.motion_control.relative_move.{axis}_move"
            await self._tag_cache.write_tag(f"{move_tag}.parameters.velocity", distance)
            await self._tag_cache.write_tag(f"{move_tag}.trigger", True)

        except Exception as e:
            error_msg = f"Failed to jog {axis} axis"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def home(self, axis: Optional[str] = None) -> None:
        """Home axis or all axes.
        
        Args:
            axis: Optional axis to home (x, y, z). If None, home all axes.
            
        Raises:
            HTTPException: If homing fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Set current position as home
            await self._tag_cache.write_tag("motion.motion_control.set_home", True)

        except Exception as e:
            error_msg = f"Failed to home {axis if axis else 'all axes'}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Health status dictionary
        """
        try:
            uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
            
            return {
                "status": "ok" if self.is_running else "error",
                "service": self._service_name,
                "version": self._version,
                "running": self.is_running,
                "uptime": uptime,
                "tag_cache": self._tag_cache is not None
            }
        except Exception as e:
            error_msg = "Failed to get health status"
            logger.error(f"{error_msg}: {str(e)}")
            return {
                "status": "error",
                "service": self._service_name,
                "version": self._version,
                "running": False,
                "error": str(e)
            }
