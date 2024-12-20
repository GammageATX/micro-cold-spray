"""Base service module."""

from typing import Dict, Any, Optional
from fastapi import status

from micro_cold_spray.api.base.base_errors import (
    create_error,
    SERVICE_ERROR,
    NOT_IMPLEMENTED,
    CONFLICT
)


class BaseService:
    """Base service with lifecycle management."""

    def __init__(self, name: Optional[str] = None):
        """Initialize service.
        
        Args:
            name: Service name (defaults to lowercase class name)
        """
        self._is_running = False
        self._name = name or self.__class__.__name__.lower()

    @property
    def name(self) -> str:
        """Get service name."""
        return self._name

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    async def start(self) -> None:
        """Start service.
        
        Raises:
            HTTPException: If service is already running (409) or fails to start (503)
        """
        if self.is_running:
            raise create_error(
                message=f"{self.name} service is already running",
                status_code=CONFLICT,
                context={"service": self.name}
            )

        try:
            await self._start()
            self._is_running = True
        except NotImplementedError as e:
            raise create_error(
                message=f"{self.name} service start not implemented",
                status_code=NOT_IMPLEMENTED,
                context={"service": self.name},
                cause=e
            )
        except Exception as e:
            raise create_error(
                message=f"Failed to start {self.name} service",
                status_code=SERVICE_ERROR,
                context={"service": self.name},
                cause=e
            )

    async def stop(self) -> None:
        """Stop service.
        
        Raises:
            HTTPException: If service is not running (409) or fails to stop (503)
        """
        if not self.is_running:
            raise create_error(
                message=f"{self.name} service is not running",
                status_code=CONFLICT,
                context={"service": self.name}
            )

        try:
            await self._stop()
            self._is_running = False
        except NotImplementedError as e:
            raise create_error(
                message=f"{self.name} service stop not implemented",
                status_code=NOT_IMPLEMENTED,
                context={"service": self.name},
                cause=e
            )
        except Exception as e:
            raise create_error(
                message=f"Failed to stop {self.name} service",
                status_code=SERVICE_ERROR,
                context={"service": self.name},
                cause=e
            )

    async def _start(self) -> None:
        """Start implementation.
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError()

    async def _stop(self) -> None:
        """Stop implementation.
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError()

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Dict with health status
        """
        try:
            return {
                "is_healthy": self.is_running,
                "status": "running" if self.is_running else "stopped",
                "service": self.name,
                "context": {
                    "service": self.name
                }
            }
        except Exception as e:
            raise create_error(
                message=f"Health check failed for {self.name} service",
                status_code=SERVICE_ERROR,
                context={"service": self.name},
                cause=e
            )
