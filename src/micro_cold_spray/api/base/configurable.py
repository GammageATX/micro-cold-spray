"""Base class for configurable services."""

from typing import Dict, Any, Optional, TYPE_CHECKING
from loguru import logger

from .service import BaseService

if TYPE_CHECKING:
    from ..config import ConfigService


class ConfigurableService(BaseService):
    """Base class for services that use configuration."""

    def __init__(self, service_name: str, config_service: 'ConfigService'):
        """Initialize configurable service.
        
        Args:
            service_name: Name of the service
            config_service: Configuration service instance
        """
        super().__init__(service_name)
        self._config: Dict[str, Any] = {}
        self._config_service = config_service
        self._config_type: Optional[str] = None

    async def _start(self) -> None:
        """Start configurable service."""
        try:
            # Load configuration if config type is set
            if self._config_type:
                config = await self._config_service.get_config(self._config_type)
                if config and config.data:
                    await self.configure(config.data)
                else:
                    logger.warning(f"No configuration found for {self._service_name} ({self._config_type})")
            elif not self._config:
                logger.warning(f"{self._service_name} starting without configuration")
                
            await super()._start()
            
        except Exception as e:
            logger.error(f"Failed to start {self._service_name}: {e}")
            raise

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

    def set_config_type(self, config_type: str) -> None:
        """Set the configuration type to load.
        
        Args:
            config_type: Type of configuration to load (e.g., 'application', 'hardware')
        """
        self._config_type = config_type
        logger.debug(f"Set config type for {self._service_name}: {config_type}")

    @property
    def config_service(self) -> 'ConfigService':
        """Get the config service instance."""
        return self._config_service
