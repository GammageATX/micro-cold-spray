"""Base class for configurable services."""

from typing import Dict, Any
from loguru import logger

from .service import BaseService


class ConfigurableService(BaseService):
    """Base class for services that use configuration."""

    def __init__(self, service_name: str):
        """Initialize configurable service."""
        super().__init__(service_name)
        self._config: Dict[str, Any] = {}

    async def _start(self) -> None:
        """Start configurable service."""
        if not self._config:
            logger.warning(f"{self._service_name} starting without configuration")
        await super()._start()

    async def configure(self, config: Dict[str, Any]) -> None:
        """Configure the service.
        
        Args:
            config: Service configuration
        """
        self._config = config
        logger.debug(f"Configured {self._service_name}")

    @property
    def config(self) -> Dict[str, Any]:
        """Get current service configuration."""
        return self._config.copy()  # Return copy to prevent modification
