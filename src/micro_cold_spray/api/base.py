"""Base service class for all APIs."""

from loguru import logger


class BaseService:
    """Base class for all API services."""

    def __init__(self):
        """Initialize base service."""
        self._initialized = False

    async def start(self) -> None:
        """Start the service."""
        if self._initialized:
            logger.warning(f"{self.__class__.__name__} already initialized")
            return

        try:
            await self._start()
            self._initialized = True
            logger.info(f"{self.__class__.__name__} started")
        except Exception as e:
            logger.error(f"Failed to start {self.__class__.__name__}: {e}")
            raise

    async def stop(self) -> None:
        """Stop the service."""
        if not self._initialized:
            logger.warning(f"{self.__class__.__name__} not initialized")
            return

        try:
            await self._stop()
            self._initialized = False
            logger.info(f"{self.__class__.__name__} stopped")
        except Exception as e:
            logger.error(f"Failed to stop {self.__class__.__name__}: {e}")
            raise

    async def _start(self) -> None:
        """Implementation specific startup."""
        pass

    async def _stop(self) -> None:
        """Implementation specific shutdown."""
        pass

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._initialized
