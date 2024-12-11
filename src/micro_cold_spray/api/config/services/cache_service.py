"""Configuration cache service."""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from ...base import BaseService
from ..models import ConfigData, ConfigMetadata
from ..exceptions import ConfigurationError


class ConfigCacheService(BaseService):
    """Service for managing configuration cache."""

    def __init__(self):
        """Initialize cache service."""
        super().__init__(service_name="config_cache")
        self._config_cache: Dict[str, ConfigData] = {}
        self._last_modified: Dict[str, float] = {}

    async def _start(self) -> None:
        """Start cache service."""
        try:
            self._config_cache.clear()
            self._last_modified.clear()
            logger.info("Config cache service started")
        except Exception as e:
            raise ConfigurationError("Failed to start cache service", {"error": str(e)})

    async def _stop(self) -> None:
        """Stop cache service."""
        try:
            self._config_cache.clear()
            self._last_modified.clear()
            logger.info("Config cache service stopped")
        except Exception as e:
            raise ConfigurationError("Failed to stop cache service", {"error": str(e)})

    def get_cached_config(self, config_type: str) -> Optional[ConfigData]:
        """Get cached configuration.
        
        Args:
            config_type: Type of config to get
            
        Returns:
            Cached config data or None if not cached
        """
        return self._config_cache.get(config_type)

    def update_cache(self, config_type: str, data: Dict[str, Any]) -> None:
        """Update cache with new config data.
        
        Args:
            config_type: Type of config to update
            data: New configuration data
        """
        metadata = ConfigMetadata(
            config_type=config_type,
            last_modified=datetime.now()
        )
        config_data = ConfigData(metadata=metadata, data=data)
        self._config_cache[config_type] = config_data
        self._last_modified[config_type] = metadata.last_modified.timestamp()

    def clear_cache(self, config_type: Optional[str] = None) -> None:
        """Clear cache entries.
        
        Args:
            config_type: Optional specific config to clear, clears all if None
        """
        if config_type:
            self._config_cache.pop(config_type, None)
            self._last_modified.pop(config_type, None)
        else:
            self._config_cache.clear()
            self._last_modified.clear()

    def is_cache_valid(self, config_type: str, file_timestamp: float) -> bool:
        """Check if cached config is still valid.
        
        Args:
            config_type: Type of config to check
            file_timestamp: File modification timestamp to compare against
            
        Returns:
            True if cache is valid
        """
        cache_conditions = (
            config_type in self._config_cache and
            config_type in self._last_modified and
            self._last_modified[config_type] >= file_timestamp
        )
        return cache_conditions

    @property
    def cache_size(self) -> int:
        """Get number of cached configs."""
        return len(self._config_cache)
