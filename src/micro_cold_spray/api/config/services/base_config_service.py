"""Base configuration service."""

from datetime import datetime
from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error


class BaseConfigService:
    """Base configuration service."""

    def __init__(self, name: str):
        """Initialize service.
        
        Args:
            name: Service name
        """
        self.name = name
        self._is_running = False
        self._start_time = None
        self._error = None

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        if not self._start_time:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    async def start(self) -> None:
        """Start service."""
        if self._is_running:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message=f"Service {self.name} already running"
            )

        try:
            await self._start()
            self._is_running = True
            self._start_time = datetime.now()
            self._error = None
            logger.info(f"{self.name} service started")
        except Exception as e:
            self._error = str(e)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start {self.name} service: {str(e)}"
            )

    async def stop(self) -> None:
        """Stop service."""
        if not self._is_running:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message=f"Service {self.name} not running"
            )

        try:
            await self._stop()
            self._is_running = False
            self._start_time = None
            self._error = None
            logger.info(f"{self.name} service stopped")
        except Exception as e:
            self._error = str(e)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop {self.name} service: {str(e)}"
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status."""
        return {
            "name": self.name,
            "status": "running" if self._is_running else "stopped",
            "is_healthy": self._is_running,
            "uptime": self.uptime,
            "error": self._error
        }

    async def _start(self) -> None:
        """Start implementation to override."""
        pass

    async def _stop(self) -> None:
        """Stop implementation to override."""
        pass
