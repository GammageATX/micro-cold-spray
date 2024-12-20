"""Motion control service implementation."""

from typing import Dict, Any, List, Tuple
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.communication.clients.base import BaseClient
from micro_cold_spray.api.communication.models.motion import Position, Velocity


class MotionService(ConfigurableService):
    """Service for controlling motion system."""

    def __init__(self, config_service: ConfigService, client: BaseClient):
        """Initialize motion service.
        
        Args:
            config_service: Configuration service instance
            client: Hardware client instance
        """
        super().__init__(service_name="motion", config_service=config_service)
        self._client = client
        self._limits: Dict[str, Tuple[float, float]] = {}

    async def _start(self) -> None:
        """Initialize service."""
        try:
            logger.debug("Loading motion configuration")
            motion_config = await self._config_service.get_config("motion")
            if not motion_config:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Motion configuration not found"
                )
                
            # Load axis limits
            self._limits = motion_config.get("limits", {})
            logger.info("Motion service initialized")
        except Exception as e:
            logger.error(f"Failed to start motion service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start motion service: {e}",
                context={"error": str(e)},
                cause=e
            )

    async def _stop(self) -> None:
        """Cleanup service."""
        self._limits.clear()
        logger.info("Motion service stopped")

    async def get_position(self) -> Position:
        """Get current position.
        
        Returns:
            Current position
            
        Raises:
            HTTPException: If position cannot be retrieved
        """
        try:
            return await self._client.get_position()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to get position",
                context={"error": str(e)},
                cause=e
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
            # Validate position against limits
            for axis, value in position.dict().items():
                if axis in self._limits:
                    min_val, max_val = self._limits[axis]
                    if value < min_val or value > max_val:
                        raise create_error(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            message=f"Position {value} out of limits for axis {axis}",
                            context={
                                "axis": axis,
                                "value": value,
                                "limits": self._limits[axis]
                            }
                        )
                        
            # Execute move
            await self._client.move_to(position, velocity)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to move to position",
                context={
                    "position": position.dict(),
                    "velocity": velocity.dict() if velocity else None,
                    "error": str(e)
                },
                cause=e
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
            # Validate all positions
            for i, position in enumerate(path):
                for axis, value in position.dict().items():
                    if axis in self._limits:
                        min_val, max_val = self._limits[axis]
                        if value < min_val or value > max_val:
                            raise create_error(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                message=f"Position {value} out of limits for axis {axis} at index {i}",
                                context={
                                    "axis": axis,
                                    "value": value,
                                    "limits": self._limits[axis],
                                    "index": i
                                }
                            )
                            
            # Execute path move
            await self._client.move_path(path, velocity)
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to move through path",
                context={
                    "path_length": len(path),
                    "velocity": velocity.dict() if velocity else None,
                    "error": str(e)
                },
                cause=e
            )

    async def stop(self) -> None:
        """Stop motion.
        
        Raises:
            HTTPException: If stop fails
        """
        try:
            await self._client.stop_motion()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to stop motion",
                context={"error": str(e)},
                cause=e
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            # Get current position
            position = await self.get_position()
            
            # Check client connection
            client_health = await self._client.check_health()
            
            return {
                "status": "ok" if client_health["status"] == "ok" else "error",
                "components": {
                    "client": client_health["status"] == "ok",
                    "position": position is not None,
                    "limits": len(self._limits) > 0
                },
                "details": client_health.get("details")
            }
        except Exception as e:
            error_msg = f"Failed to check motion health: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
