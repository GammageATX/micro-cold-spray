"""Configuration cache service."""

from datetime import datetime
from typing import Dict, Optional

from loguru import logger

from micro_cold_spray.api.base import BaseService
from micro_cold_spray.api.config.models import ConfigData


class ConfigCacheService(BaseService):
    """Service for caching configuration data."""

    def __init__(self):
        """Initialize cache service."""
        super().__init__(service_name="config_cache")
        self._cache: Dict[str, ConfigData] = {}
        self._last_update: Optional[datetime] = None

    async def _start(self) -> None:
        """Start the cache service."""
        try:
            self._cache = {}
            self._last_update = None
            logger.info("Cache service started successfully")
        except Exception as e:
            logger.error(f"Failed to start cache service: {e}")
            raise

    async def _stop(self) -> None:
        """Stop the cache service."""
        try:
            self._cache = {}
            self._last_update = None
            logger.info("Cache service stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop cache service: {e}")
            raise

    async def get_cached_config(self, config_type: str) -> Optional[ConfigData]:
        """Get cached configuration data.
        
        Args:
            config_type: Type of configuration to get
            
        Returns:
            Cached configuration data or None if not found
        """
        return self._cache.get(config_type)

    async def cache_config(self, config_type: str, config_data: ConfigData) -> None:
        """Cache configuration data.
        
        Args:
            config_type: Type of configuration to cache
            config_data: Configuration data to cache
        """
        self._cache[config_type] = config_data
        self._last_update = datetime.now()

    async def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache = {}
        self._last_update = None

    async def remove_from_cache(self, config_type: str) -> None:
        """Remove configuration from cache.
        
        Args:
            config_type: Type of configuration to remove
        """
        if config_type in self._cache:
            del self._cache[config_type]

    @property
    def cache_size(self) -> int:
        """Get number of cached configurations."""
        return len(self._cache)

    @property
    def last_update(self) -> Optional[datetime]:
        """Get timestamp of last cache update."""
        return self._last_update
