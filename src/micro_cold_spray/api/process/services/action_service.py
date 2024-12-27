"""Action service for process execution."""

from datetime import datetime
import time
from typing import Dict, List, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils import ServiceHealth, get_uptime
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
                details={"error": str(e)}
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
                details={"error": str(e)}
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
                details={"error": str(e)}
            )

    async def health(self) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Health status
        """
        try:
            return ServiceHealth(
                status="ok",
                service=self._service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None,
                components={}
            )
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service=self._service_name,
                version=self.version,
                is_running=False,
                uptime=0.0,
                error=error_msg,
                components={}
            )

    async def start_action(self, action_id: str) -> ActionStatus:
        """Start action execution.
        
        Args:
            action_id: Action ID
            
        Returns:
            Action status
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running",
                    details={"action_id": action_id}
                )

            if self._current_action:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Action already in progress",
                    details={"action_id": action_id, "current_action": self._current_action}
                )

            self._current_action = action_id
            logger.info(f"Started action: {action_id}")
            return ActionStatus.RUNNING

        except Exception as e:
            logger.error(f"Failed to start action: {str(e)}")
            raise

    async def stop_action(self, action_id: str) -> ActionStatus:
        """Stop action execution.
        
        Args:
            action_id: Action ID
            
        Returns:
            Action status
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running",
                    details={"action_id": action_id}
                )

            if not self._current_action:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="No action in progress",
                    details={"action_id": action_id}
                )

            if self._current_action != action_id:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Action not in progress",
                    details={"action_id": action_id, "current_action": self._current_action}
                )

            self._current_action = None
            logger.info(f"Stopped action: {action_id}")
            return ActionStatus.COMPLETED

        except Exception as e:
            logger.error(f"Failed to stop action: {str(e)}")
            raise

    async def get_action_status(self, action_id: str) -> ActionStatus:
        """Get action execution status.
        
        Args:
            action_id: Action ID
            
        Returns:
            Action status
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running",
                    details={"action_id": action_id}
                )

            if not self._current_action:
                return ActionStatus.IDLE

            if self._current_action != action_id:
                return ActionStatus.IDLE

            return ActionStatus.RUNNING

        except Exception as e:
            logger.error(f"Failed to get action status: {str(e)}")
            raise
