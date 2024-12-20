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
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Service is already running",
                context={"service": self.name}
            )
        
        await self._start()
        self._is_running = True

    async def stop(self) -> None:
        """Stop the service."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Service is not running",
                context={"service": self.name}
            )
        
        await self._stop()
        self._is_running = False

    async def _start(self) -> None:
        """Start implementation."""
        raise create_error(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            message="Service does not implement start",
            context={"service": self.name}
        )

    async def _stop(self) -> None:
        """Stop implementation."""
        raise create_error(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            message="Service does not implement stop",
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
