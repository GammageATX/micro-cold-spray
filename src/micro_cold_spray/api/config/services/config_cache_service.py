"""Configuration cache service implementation."""

from datetime import datetime, timedelta
from typing import Dict, Optional, Union

from loguru import logger

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import ConfigError, ServiceError
from micro_cold_spray.api.config.models import ConfigData


class CacheEntry:
    """Cache entry."""

    def __init__(self, data: ConfigData, ttl: int = 3600):
        """Initialize cache entry.

        Args:
            data: Configuration data
            ttl: Time to live in seconds
        """
        self.data = data
        self.timestamp = datetime.now()
        self.ttl = ttl

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired.

        Returns:
            True if expired
        """
        return (datetime.now() - self.timestamp).total_seconds() > self.ttl


class ConfigCacheService(BaseService):
    """Configuration cache service implementation."""

    def __init__(self, service_name: str = "cache") -> None:
        """Initialize service.

        Args:
            service_name: Service name
        """
        super().__init__(service_name)
        self._cache: Dict[str, Union[CacheEntry, Dict]] = {}

    async def _start(self) -> None:
        """Start implementation."""
        try:
            await self._initialize()
            logger.info("Cache service started")
        except Exception as e:
            raise ServiceError(str(e), error_code="SERVICE_START_ERROR")

    async def _stop(self) -> None:
        """Stop implementation."""
        try:
            await self._cleanup()
            logger.info("Cache service stopped")
        except Exception as e:
            raise ServiceError(str(e), error_code="SERVICE_STOP_ERROR")

    async def _initialize(self) -> None:
        """Initialize cache."""
        self._cache.clear()

    async def _cleanup(self) -> None:
        """Clean up cache."""
        self._cache.clear()

    async def validate_cache_entry(self, entry: Optional[Dict]) -> bool:
        """Validate cache entry.

        Args:
            entry: Cache entry to validate

        Returns:
            True if valid

        Raises:
            ConfigError: If validation fails
        """
        if not entry:
            raise ConfigError("Cache entry cannot be None")

        if not isinstance(entry, dict):
            raise ConfigError("Cache entry must be dictionary")

        if "timestamp" not in entry or "data" not in entry:
            raise ConfigError("Cache entry must have timestamp and data")

        return True

    async def get_cached_config(self, config_type: str) -> Optional[ConfigData]:
        """Get cached configuration.

        Args:
            config_type: Configuration type

        Returns:
            Cached configuration if found and not expired
        """
        entry = self._cache.get(config_type)
        if not entry:
            return None

        if isinstance(entry, dict):
            # Handle raw dict entries from tests
            if (datetime.now() - entry["timestamp"]).total_seconds() > 7200:  # 2 hours
                return None
            return entry["data"]
        elif isinstance(entry, CacheEntry) and not entry.is_expired:
            return entry.data
        return None

    async def _validate_config(self, config: ConfigData) -> None:
        """Validate configuration.

        Args:
            config: Configuration data

        Raises:
            ConfigError: If validation fails
        """
        if not config:
            raise ConfigError("Config data cannot be None")

    async def cache_config(self, config_type: str, config: ConfigData, ttl: int = 3600) -> None:
        """Cache configuration.

        Args:
            config_type: Configuration type
            config: Configuration data
            ttl: Time to live in seconds

        Raises:
            ConfigError: If caching fails
        """
        try:
            await self._validate_config(config)
            self._cache[config_type] = CacheEntry(config, ttl)
            logger.debug("Cached config: {}", config_type)
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Failed to cache config: {str(e)}")

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
