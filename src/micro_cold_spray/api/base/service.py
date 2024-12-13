"""Base service class for all APIs."""

from datetime import datetime
from loguru import logger


class BaseService:
    """Base class for all API services."""

    def __init__(self, service_name: str):
        """Initialize base service."""
        self._service_name = service_name
        self._initialized = False
        self.start_time = datetime.now()
        self.version = "1.0.0"

    async def start(self) -> None:
        """Start the service."""
        if self._initialized:
            logger.warning(f"{self._service_name} already initialized")
            return

        try:
            # Service-specific startup
            await self._start()
            self._initialized = True
            logger.info(f"{self._service_name} started")
        except Exception as e:
            logger.error(f"Failed to start {self._service_name}: {e}")
            raise

    async def stop(self) -> None:
        """Stop the service."""
        if not self._initialized:
            logger.warning(f"{self._service_name} not initialized")
            return

        try:
            await self._stop()
            self._initialized = False
            logger.info(f"{self._service_name} stopped")
        except Exception as e:
            logger.error(f"Failed to stop {self._service_name}: {e}")
            raise

    async def _start(self) -> None:
        """Implementation specific startup. Override in derived classes."""
        pass

    async def _stop(self) -> None:
        """Implementation specific shutdown. Override in derived classes."""
        pass

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._initialized
