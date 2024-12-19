"""Base service functionality."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .base_errors import ServiceError, AppErrorCode


class BaseService:
    """Base service class."""

    def __init__(self, service_name: str, dependencies: Optional[List[str]] = None):
        """Initialize base service.
        
        Args:
            service_name: Name of the service
            dependencies: List of service names this service depends on
        """
        self._service_name = service_name
        self._dependencies = dependencies or []
        self._is_running = False
        self._is_initialized = False
        self._start_time: Optional[datetime] = None
        self._metrics = {
            "start_count": 0,
            "stop_count": 0,
            "error_count": 0,
            "last_error": None
        }

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def dependencies(self) -> List[str]:
        """Get service dependencies."""
        return self._dependencies

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._is_initialized

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return self._metrics.copy()

    @property
    def uptime(self) -> timedelta:
        """Get service uptime."""
        if not self._start_time:
            return timedelta()
        return datetime.now() - self._start_time

    async def _start(self) -> None:
        """Start implementation.
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _start")

    async def _stop(self) -> None:
        """Stop implementation.
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _stop")

    async def start(self) -> None:
        """Start service.
        
        Raises:
            ServiceError: If service fails to start
        """
        if self.is_running:
            return

        try:
            await self._start()
            self._is_running = True
            self._is_initialized = True
            self._start_time = datetime.now()
            self._metrics["start_count"] += 1
        except Exception as e:
            self._metrics["error_count"] += 1
            self._metrics["last_error"] = str(e)
            raise ServiceError(
                f"Failed to start service: {e}",
                error_code=AppErrorCode.SERVICE_START_ERROR
            ) from e

    async def stop(self) -> None:
        """Stop service.
        
        Raises:
            ServiceError: If service fails to stop
        """
        if not self.is_running:
            return

        try:
            await self._stop()
            self._is_running = False
            self._start_time = None
            self._metrics["stop_count"] += 1
        except Exception as e:
            self._metrics["error_count"] += 1
            self._metrics["last_error"] = str(e)
            raise ServiceError(
                f"Failed to stop service: {e}",
                error_code=AppErrorCode.SERVICE_STOP_ERROR
            ) from e

    async def check_health(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Dict containing health check information
            
        Raises:
            ServiceError: If health check fails
        """
        if not self.is_running:
            self._metrics["error_count"] += 1
            self._metrics["last_error"] = "Service is not running"
            raise ServiceError(
                "Health check failed: Service is not running",
                error_code=AppErrorCode.SERVICE_NOT_RUNNING
            )

        return {
            "status": "ok",
            "service_info": {
                "name": self.service_name,
                "running": self.is_running,
                "uptime": str(self.uptime),
                "metrics": self.metrics
            }
        }
