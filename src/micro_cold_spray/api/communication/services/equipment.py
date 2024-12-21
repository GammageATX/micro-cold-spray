"""Equipment control service implementation."""

from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error


class EquipmentService:
    """Service for controlling equipment state."""

    def __init__(self):
        """Initialize equipment service."""
        self._service_name = "equipment"
        self._is_running = False
        logger.info("EquipmentService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def start(self) -> None:
        """Start equipment service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            self._is_running = True
            logger.info("Equipment service started")

        except Exception as e:
            error_msg = f"Failed to start equipment service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop equipment service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running"
                )

            self._is_running = False
            logger.info("Equipment service stopped")

        except Exception as e:
            error_msg = f"Failed to stop equipment service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def get_state(self) -> Dict[str, Any]:
        """Get current equipment state.
        
        Returns:
            Current equipment state
            
        Raises:
            HTTPException: If state cannot be retrieved
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Mock state for now
            return {
                "power": "on",
                "temperature": 25.0,
                "pressure": 1.0
            }

        except Exception as e:
            error_msg = "Failed to get equipment state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_state(self, state: Dict[str, Any]) -> None:
        """Set equipment state.
        
        Args:
            state: Desired equipment state
            
        Raises:
            HTTPException: If state cannot be set
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Mock state update for now
            logger.info(f"Setting equipment state to {state}")

        except Exception as e:
            error_msg = "Failed to set equipment state"
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
            "running": self.is_running
        }
