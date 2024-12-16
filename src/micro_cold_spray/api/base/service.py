"""Base service class for all APIs."""

from datetime import datetime
from loguru import logger
from .exceptions import ServiceError


class BaseService:
    """Base service class."""

    def __init__(self, service_name: str):
        """Initialize service."""
        self._service_name = service_name
        self._initialized = False
        self._running = False
        self.start_time = datetime.now()
        self._error = None
        self.version = "1.0.0"

    async def start(self):
        """Start service."""
        if self._running:
            raise ServiceError(f"{self._service_name} already running")

        try:
            await self._start()
            self._initialized = True
            self._running = True
            self.start_time = datetime.now()
            self._error = None
            logger.info(f"{self._service_name} started")
        except Exception as e:
            self._running = False
            self._error = str(e)
            logger.error(f"Failed to start {self._service_name}: {e}")
            raise

    async def stop(self):
        """Stop service."""
        if not self._running:
            logger.warning(f"{self._service_name} not running")
            return

        try:
            await self._stop()
            self._running = False
            logger.info(f"{self._service_name} stopped")
        except Exception as e:
            logger.error(f"Failed to stop {self._service_name}: {e}")
            raise

    @property
    def is_running(self) -> bool:
        """Return whether service is running."""
        return self._running

    @property
    def is_initialized(self) -> bool:
        """Return whether service is initialized."""
        return self._initialized

    @property
    def error(self) -> str:
        """Return last error message."""
        return self._error

    async def _start(self):
        """Start service implementation."""
        pass

    async def _stop(self):
        """Stop service implementation."""
        pass

    async def check_health(self):
        """Check service health."""
        return {
            "status": "ok" if self.is_running else "stopped",
            "error": self._error
        }
