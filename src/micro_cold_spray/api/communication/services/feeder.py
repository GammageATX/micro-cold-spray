"""Feeder control service implementation."""

from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error


class FeederService:
    """Service for controlling powder feeder."""

    def __init__(self):
        """Initialize feeder service."""
        self._service_name = "feeder"
        self._is_running = False
        logger.info("FeederService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def start(self) -> None:
        """Start feeder service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running",
                    context={"service": self._service_name}
                )

            self._is_running = True
            logger.info("Feeder service started")

        except Exception as e:
            error_msg = f"Failed to start feeder service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"service": self._service_name}
            )

    async def stop(self) -> None:
        """Stop feeder service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running",
                    context={"service": self._service_name}
                )

            self._is_running = False
            logger.info("Feeder service stopped")

        except Exception as e:
            error_msg = f"Failed to stop feeder service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"service": self._service_name}
            )

    async def get_state(self) -> Dict[str, Any]:
        """Get current feeder state.
        
        Returns:
            Current feeder state
            
        Raises:
            HTTPException: If state cannot be retrieved
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running",
                    context={"service": self._service_name}
                )

            # Mock state for now
            return {
                "power": "on",
                "feed_rate": 2.5,
                "hopper_level": 75.0
            }

        except Exception as e:
            error_msg = "Failed to get feeder state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def set_state(self, state: Dict[str, Any]) -> None:
        """Set feeder state.
        
        Args:
            state: Desired feeder state
            
        Raises:
            HTTPException: If state cannot be set
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running",
                    context={"service": self._service_name}
                )

            # Mock state update for now
            logger.info(f"Setting feeder state to {state}")

        except Exception as e:
            error_msg = "Failed to set feeder state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"state": state}
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
