"""Configuration cache service implementation."""

from datetime import datetime, timedelta
from typing import Dict, Optional

from loguru import logger

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import ConfigError
from micro_cold_spray.api.config.models.config_models import ConfigData


class CacheEntry:
    """Cache entry."""

    def __init__(self, config: ConfigData, ttl: int = 3600) -> None:
        """Initialize cache entry.

        Args:
            config: Configuration data
            ttl: Time to live in seconds
        """
        self.config = config
        self.timestamp = datetime.now()
        self.ttl = ttl

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired.

        Returns:
            True if expired
        """
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl)


class ConfigCacheService(BaseService):
    """Configuration cache service implementation."""

    def __init__(self, service_name: str) -> None:
        """Initialize service.

        Args:
            service_name: Service name
        """
        super().__init__(service_name)
        self._cache: Dict[str, CacheEntry] = {}

    async def _start(self) -> None:
        """Start cache service."""
        try:
            self._cache.clear()
            logger.info("Cache service started")
        except Exception as e:
            raise ConfigError("Failed to start cache service", {"error": str(e)})

    async def _stop(self) -> None:
        """Stop cache service."""
        try:
            self._cache.clear()
            logger.info("Cache service stopped")
        except Exception as e:
            raise ConfigError("Failed to stop cache service", {"error": str(e)})

    def get_cached_config(self, config_type: str) -> Optional[ConfigData]:
        """Get cached configuration.

        Args:
            config_type: Configuration type

        Returns:
            Cached configuration if found and not expired
        """
        entry = self._cache.get(config_type)
        if entry and not entry.is_expired:
            return entry.config
        return None

    async def cache_config(self, config: ConfigData, ttl: int = 3600) -> None:
        """Cache configuration.

        Args:
            config: Configuration data
            ttl: Time to live in seconds

        Raises:
            ConfigError: If caching fails
        """
        if not config:
            raise ConfigError("Config data cannot be None")

        try:
            self._cache[config.metadata.config_type] = CacheEntry(config, ttl)
            logger.debug("Cached config: {}", config.metadata.config_type)
        except Exception as e:
            raise ConfigError("Failed to cache config", {"error": str(e)})

    async def clear_cache(self) -> None:
        """Clear cache."""
        self._cache.clear()
        logger.info("Cache cleared")

    async def check_health(self) -> dict:
        """Check service health.

        Returns:
            Health check result
        """
        health = await super().check_health()
        health["service_info"].update({
            "cache_size": len(self._cache),
            "cached_types": list(self._cache.keys())
        })
        return health
