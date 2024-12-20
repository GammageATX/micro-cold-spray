"""Base service module."""

from typing import Dict, Any
from fastapi import status

from .base_errors import create_http_error


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
            raise ValueError("Service is already running")
        
        await self._start()
        self._is_running = True

    async def stop(self) -> None:
        """Stop the service."""
        if not self.is_running:
            raise ValueError("Service is not running")
        
        self._is_running = False
        await self._stop()

    async def _start(self) -> None:
        """Start implementation."""
        raise ValueError("Service does not implement start")

    async def _stop(self) -> None:
        """Stop implementation."""
        raise ValueError("Service does not implement stop")

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
