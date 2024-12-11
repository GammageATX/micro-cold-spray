"""Base service class for all APIs."""

from typing import Any, Dict, Optional
from loguru import logger

from ..config import ConfigService


class BaseService:
    """Base class for all API services."""

    def __init__(self, service_name: str, config_service: Optional[ConfigService] = None):
        """Initialize base service."""
        self._service_name = service_name
        self._initialized = False
        self._config_service = config_service
        self._config: Dict[str, Any] = {}

    async def start(self) -> None:
        """Start the service."""
        if self._initialized:
            logger.warning(f"{self._service_name} already initialized")
            return

        try:
            # Load config if service provided
            if self._config_service:
                await self._load_config()
                await self._config_service.subscribe(
                    "config/update/*",
                    self._handle_config_update
                )

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

    async def _load_config(self) -> None:
        """Load service configuration."""
        if not self._config_service:
            return
            
        try:
            self._config = await self._config_service.get_config(self._service_name)
            logger.debug(f"Loaded config for {self._service_name}")
        except Exception as e:
            logger.error(f"Failed to load config for {self._service_name}: {e}")
            raise

    async def _handle_config_update(self, _: Dict[str, Any]) -> None:
        """Handle configuration updates.
        
        Default behavior is to restart the service with new config.
        Override in derived classes for custom update handling.
        """
        logger.info(f"{self._service_name} restarting due to config update")
        await self.stop()
        await self.start()

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._initialized

    @property
    def config(self) -> Dict[str, Any]:
        """Get current service configuration."""
        return self._config.copy()  # Return copy to prevent modification
