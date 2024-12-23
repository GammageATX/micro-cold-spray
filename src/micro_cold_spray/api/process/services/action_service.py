"""Action service for process execution."""

from datetime import datetime
import time
from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.models.process_models import ActionStatus


class ActionService:
    """Service for managing process actions."""

    def __init__(self):
        """Initialize action service."""
        self._service_name = "action"
        self._version = "1.0.0"
        self._start_time = None
        self._is_running = False
        self._current_action = None
        logger.info("ActionService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self._start_time.timestamp() if self._start_time else 0

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            logger.info("Action service initialized")
        except Exception as e:
            error_msg = f"Failed to initialize action service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"error": str(e)}
            )

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            self._start_time = datetime.now()
            self._is_running = True
            logger.info("Action service started")

        except Exception as e:
            error_msg = f"Failed to start action service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"error": str(e)}
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running"
                )

            self._is_running = False
            self._start_time = None
            logger.info("Action service stopped")

        except Exception as e:
            error_msg = f"Failed to stop action service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"error": str(e)}
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Health status dictionary
        """
        return {
            "status": "ok" if self.is_running else "error",
            "service": self._service_name,
            "version": self._version,
            "running": self.is_running,
            "uptime": self.uptime,
            "current_action": self._current_action
        }

    async def start_action(self, action_id: str) -> ActionStatus:
        """Start action execution.
        
        Args:
            action_id: Action identifier
            
        Returns:
            Action status
            
        Raises:
            HTTPException: If start fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if self._current_action:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Another action is already running",
                    context={"current_action": self._current_action}
                )

            self._current_action = action_id
            logger.info(f"Started action: {action_id}")
            return ActionStatus.RUNNING

        except Exception as e:
            error_msg = f"Failed to start action {action_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def stop_action(self, action_id: str) -> ActionStatus:
        """Stop action execution.
        
        Args:
            action_id: Action identifier
            
        Returns:
            Action status
            
        Raises:
            HTTPException: If stop fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if not self._current_action:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="No action is running"
                )

            if self._current_action != action_id:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"Action {action_id} is not running",
                    context={
                        "action_id": action_id,
                        "current_action": self._current_action
                    }
                )

            self._current_action = None
            logger.info(f"Stopped action: {action_id}")
            return ActionStatus.COMPLETED

        except Exception as e:
            error_msg = f"Failed to stop action {action_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )

    async def get_action_status(self, action_id: str) -> ActionStatus:
        """Get action execution status.
        
        Args:
            action_id: Action identifier
            
        Returns:
            Action status
            
        Raises:
            HTTPException: If status check fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if not self._current_action:
                return ActionStatus.IDLE

            if self._current_action != action_id:
                return ActionStatus.IDLE

            return ActionStatus.RUNNING

        except Exception as e:
            error_msg = f"Failed to get status for action {action_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"error": str(e)}
            )
