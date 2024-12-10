from typing import Any, Dict
from loguru import logger
from ....core.infrastructure.config.config_manager import ConfigManager


class BaseService:
    """Base class for services that need config access."""

    def __init__(self, config_manager: ConfigManager):
        self._config_manager = config_manager
        self._tag_config: Dict[str, Any] = {}
        self._hw_config: Dict[str, Any] = {}

    async def initialize(self):
        """Load configurations and subscribe to updates."""
        await self._load_configs()
        await self._config_manager.subscribe("config/update/*", self._handle_config_update)
        logger.info(f"{self.__class__.__name__} initialized")

    async def shutdown(self):
        """Cleanup before restart."""
        logger.info(f"{self.__class__.__name__} shutting down")

    async def _load_configs(self):
        """Load all configurations."""
        tag_config = await self._config_manager.get_config('tags')
        self._tag_config = tag_config.get('tag_groups', {})
        hw_config = await self._config_manager.get_config('hardware')
        self._hw_config = hw_config.get('hardware', {})

    async def _handle_config_update(self, _):
        """Handle any config update by triggering service restart."""
        logger.info(f"{self.__class__.__name__} restarting due to config update")
        await self.shutdown()
        await self.initialize()
