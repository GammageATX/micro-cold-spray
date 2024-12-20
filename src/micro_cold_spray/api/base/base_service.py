"""Base service module."""

from typing import Dict, Any
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error


class BaseService:
    """Base service class."""

    def __init__(self, name: str = None):
        """Initialize base service.
        
        Args:
            name: Service name (optional)
        """
        self.name = name or self.__class__.__name__.lower()
        self._is_running = False

    async def start(self) -> None:
        """Start the service."""
        if self.is_running:
            raise create_error(
                message=f"{self.name} service is already running",
                status_code=status.HTTP_409_CONFLICT,
                context={"service": self.name}
            )
        
        try:
            await self._start()
            self._is_running = True
        except Exception as e:
            raise create_error(
                message=f"Failed to start {self.name} service",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                context={"service": self.name},
                cause=e
            )

    async def stop(self) -> None:
        """Stop the service."""
        if not self.is_running:
            raise create_error(
                message=f"{self.name} service is not running",
                status_code=status.HTTP_409_CONFLICT,
                context={"service": self.name}
            )
        
        try:
            await self._stop()
            self._is_running = False
        except Exception as e:
            raise create_error(
                message=f"Failed to stop {self.name} service",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                context={"service": self.name},
                cause=e
            )

    async def _start(self) -> None:
        """Start implementation."""
        raise create_error(
            message=f"{self.name} service does not implement start",
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            context={"service": self.name}
        )

    async def _stop(self) -> None:
        """Stop implementation."""
        raise create_error(
            message=f"{self.name} service does not implement stop",
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            context={"service": self.name}
        )

    async def health(self) -> Dict[str, Any]:
        """Get service health status."""
        return {
            "is_healthy": self.is_running,
            "status": "running" if self.is_running else "stopped",
            "context": {
                "service": self.name
            }
        }

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running
