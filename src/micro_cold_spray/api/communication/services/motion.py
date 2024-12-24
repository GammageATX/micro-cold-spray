"""Motion control service implementation."""

from typing import Dict, Any, List, Tuple
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.models.motion import Position, Velocity


class MotionService:
    """Service for controlling motion system."""

    def __init__(self):
        """Initialize motion service."""
        self._service_name = "motion"
        self._limits: Dict[str, Tuple[float, float]] = {}
        self._is_running = False
        logger.info("MotionService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def start(self) -> None:
        """Start motion service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Initialize service
            self._limits.clear()
            self._is_running = True
            logger.info("Motion service started")

        except Exception as e:
            error_msg = f"Failed to start motion service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop motion service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running"
                )

            self._limits.clear()
            self._is_running = False
            logger.info("Motion service stopped")

        except Exception as e:
            error_msg = f"Failed to stop motion service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def get_position(self) -> Position:
        """Get current position.
        
        Returns:
            Current position
            
        Raises:
            HTTPException: If position cannot be retrieved
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Mock position for now
            return Position(x=0.0, y=0.0, z=0.0)

        except Exception as e:
            error_msg = "Failed to get position"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def move_to(self, position: Position, velocity: Velocity = None) -> None:
        """Move to position.
        
        Args:
            position: Target position
            velocity: Optional velocity override
            
        Raises:
            HTTPException: If move fails or position out of limits
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate position against limits
            for axis, value in position.dict().items():
                if axis in self._limits:
                    min_val, max_val = self._limits[axis]
                    if value < min_val or value > max_val:
                        raise create_error(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            message=f"Position {value} out of limits for axis {axis}"
                        )

            # Mock move for now
            logger.info(f"Moving to position {position} with velocity {velocity}")

        except Exception as e:
            error_msg = "Failed to move to position"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def move_path(self, path: List[Position], velocity: Velocity = None) -> None:
        """Move through path.
        
        Args:
            path: List of positions to move through
            velocity: Optional velocity override
            
        Raises:
            HTTPException: If move fails or any position out of limits
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate all positions
            for i, position in enumerate(path):
                for axis, value in position.dict().items():
                    if axis in self._limits:
                        min_val, max_val = self._limits[axis]
                        if value < min_val or value > max_val:
                            raise create_error(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                message=f"Position {value} out of limits for axis {axis} at index {i}"
                            )

            # Mock path move for now
            logger.info(f"Moving through path of {len(path)} points with velocity {velocity}")

        except Exception as e:
            error_msg = "Failed to move through path"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def stop_motion(self) -> None:
        """Stop motion.
        
        Raises:
            HTTPException: If stop fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Mock stop for now
            logger.info("Stopping motion")

        except Exception as e:
            error_msg = "Failed to stop motion"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Health status dictionary
        """
        return {
            "status": "ok" if self.is_running else "error",
            "service": self._service_name,
            "running": self.is_running,
            "limits": len(self._limits)
        }
