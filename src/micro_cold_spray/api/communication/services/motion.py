"""Motion service implementation."""

from typing import Dict, Any, Optional, Callable, List
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
        self._state_changed_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        logger.info("MotionService initialized")

    def on_state_changed(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for state changes.
        
        Args:
            callback: Function to call when state changes
        """
        self._state_changed_callbacks.append(callback)

    def remove_state_changed_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Remove state change callback.
        
        Args:
            callback: Callback to remove
        """
        if callback in self._state_changed_callbacks:
            self._state_changed_callbacks.remove(callback)

    async def _notify_state_changed(self) -> None:
        """Notify all registered callbacks of state change."""
        try:
            position = await self.get_position()
            status = await self.get_status()
            state = {
                "position": position.dict(),
                "status": status.dict()
            }
            for callback in self._state_changed_callbacks:
                try:
                    callback(state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {str(e)}")
        except Exception as e:
            logger.error(f"Error notifying state change: {str(e)}")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    def set_tag_cache(self, tag_cache: TagCacheService) -> None:
        """Set tag cache service.
        
        Args:
            tag_cache: Tag cache service
        """
        self._tag_cache = tag_cache
        logger.info("Tag cache service set")

    async def initialize(self) -> None:
        """Initialize motion service.
        
        Raises:
            HTTPException: If initialization fails
        """
        try:
            if not self._tag_cache:
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Tag cache service not set"
                )
            
            self._is_running = False
            self._start_time = None
            logger.info("Motion service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize motion service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start motion service.
        
        Raises:
            HTTPException: If startup fails
        """
        try:
            if not self._tag_cache:
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Tag cache service not set"
                )
            
            self._is_running = True
            self._start_time = datetime.now()
            logger.info("Motion service started")
            
        except Exception as e:
            error_msg = f"Failed to start motion service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop motion service.
        
        Raises:
            HTTPException: If shutdown fails
        """
        try:
            self._is_running = False
            self._start_time = None
            logger.info("Motion service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop motion service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

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

            # Read current position from AMC controller
            x = await self._tag_cache.get_tag("motion.motion_control.coordinated_move.xy_move.parameters.x_position")
            y = await self._tag_cache.get_tag("motion.motion_control.coordinated_move.xy_move.parameters.y_position")
            z = await self._tag_cache.get_tag("motion.motion_control.relative_move.z_move.parameters.position")

            # Default to 0 if position is None
            x = x if x is not None else 0.0
            y = y if y is not None else 0.0
            z = z if z is not None else 0.0

            return Position(x=x, y=y, z=z)

        except Exception as e:
            error_msg = "Failed to get position"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def get_status(self) -> SystemStatus:
        """Get system status.
        
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

            # Get axis statuses
            x_status = await self.get_axis_status("x")
            y_status = await self.get_axis_status("y")
            z_status = await self.get_axis_status("z")

            # Get module ready status
            module_ready = await self._tag_cache.get_tag("interlocks.motion_ready")
            if module_ready is None:
                module_ready = False

            return SystemStatus(
                x_axis=x_status,
                y_axis=y_status,
                z_axis=z_status,
                module_ready=module_ready
            )

        except Exception as e:
            error_msg = "Failed to get system status"
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

            # Get axis status
            if axis in ["x", "y"]:
                # For X and Y axes, use coordinated move status
                position = await self._tag_cache.get_tag(f"motion.motion_control.coordinated_move.xy_move.parameters.{axis}_position")
                in_progress = await self._tag_cache.get_tag("motion.motion_control.coordinated_move.xy_move.parameters.in_progress")
                complete = await self._tag_cache.get_tag("motion.motion_control.coordinated_move.xy_move.parameters.status")
            else:
                # For Z axis, use relative move status
                position = await self._tag_cache.get_tag(f"motion.motion_control.relative_move.{axis}_move.parameters.position")
                in_progress = await self._tag_cache.get_tag(f"motion.motion_control.relative_move.{axis}_move.parameters.in_progress")
                complete = await self._tag_cache.get_tag(f"motion.motion_control.relative_move.{axis}_move.parameters.status")

            # Parse status
            moving = bool(in_progress)  # Moving if in progress
            in_position = bool(complete)  # In position if move completed
            error = not await self._tag_cache.get_tag("interlocks.motion_ready")  # Error if not enabled
            homed = bool(complete)  # Consider homed if last move completed

            # Default to 0 if position is None
            position = position if position is not None else 0.0

            return AxisStatus(
                position=position,
                in_position=in_position,
                moving=moving,
                error=error,
                homed=homed
            )

        except Exception as e:
            error_msg = f"Failed to get {axis} axis status"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def move(self, x: float, y: float, z: float, velocity: float, wait_complete: bool = True) -> None:
        """Move to position.
        
        Args:
            x: X position
            y: Y position
            z: Z position
            velocity: Move velocity
            wait_complete: Wait for move to complete
            
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
            await self._tag_cache.set_tag("motion.motion_control.coordinated_move.xy_move.parameters.x_position", x)
            await self._tag_cache.set_tag("motion.motion_control.coordinated_move.xy_move.parameters.y_position", y)
            await self._tag_cache.set_tag("motion.motion_control.coordinated_move.xy_move.parameters.velocity", velocity)
            
            # Trigger XY move
            await self._tag_cache.set_tag("motion.motion_control.coordinated_move.xy_move.trigger", True)
            
            # Set Z position and trigger move
            await self._tag_cache.set_tag("motion.motion_control.relative_move.z_move.parameters.position", z)
            await self._tag_cache.set_tag("motion.motion_control.relative_move.z_move.parameters.velocity", velocity)
            await self._tag_cache.set_tag("motion.motion_control.relative_move.z_move.trigger", True)

            # Notify state change
            await self._notify_state_changed()

        except Exception as e:
            error_msg = "Failed to move"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def jog_axis(self, axis: str, distance: float, velocity: float) -> None:
        """Jog axis by distance.
        
        Args:
            axis: Axis to jog (x, y, z)
            distance: Jog distance
            velocity: Jog velocity
            
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
            await self._tag_cache.set_tag(f"{move_tag}.parameters.position", distance)
            await self._tag_cache.set_tag(f"{move_tag}.parameters.velocity", velocity)
            await self._tag_cache.set_tag(f"{move_tag}.trigger", True)

            # Notify state change
            await self._notify_state_changed()

        except Exception as e:
            error_msg = f"Failed to jog {axis} axis"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_home(self) -> None:
        """Set current position as home.
            
        Raises:
            HTTPException: If setting home fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Set current position as home
            await self._tag_cache.set_tag("motion.motion_control.set_home", True)

            # Notify state change
            await self._notify_state_changed()

        except Exception as e:
            error_msg = "Failed to set home"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def move_to_home(self) -> None:
        """Move to home position.
            
        Raises:
            HTTPException: If move fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Trigger move to home
            await self._tag_cache.set_tag("motion.motion_control.move_to_home", True)

            # Notify state change
            await self._notify_state_changed()

        except Exception as e:
            error_msg = "Failed to move to home"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Dict[str, Any]: Health status dictionary
        """
        try:
            return {
                "status": "ok" if self.is_running else "error",
                "service_name": self._service_name,
                "version": self._version,
                "is_running": self.is_running,
                "uptime": (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
                "error": None if self.is_running else "Service not running",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            error_msg = f"Failed to get health status: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "service_name": self._service_name,
                "version": self._version,
                "is_running": False,
                "uptime": 0,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
