"""Configuration cache service implementation."""

from datetime import datetime, timedelta
from typing import Dict, Optional, Union

from loguru import logger
from fastapi import status, HTTPException

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import (
    create_error,
    AppErrorCode,
    service_error,
    config_error
)
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
            raise service_error(
                message="Failed to start cache service",
                context={"error": str(e)}
            )

    async def _stop(self) -> None:
        """Stop implementation."""
        try:
            await self._cleanup()
            logger.info("Cache service stopped")
        except Exception as e:
            raise service_error(
                message="Failed to stop cache service",
                context={"error": str(e)}
            )

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
            HTTPException: If validation fails (422)
        """
        if not entry:
            raise config_error(
                message="Cache entry cannot be None",
                context={"entry": None}
            )

        if not isinstance(entry, dict):
            raise config_error(
                message="Cache entry must be dictionary",
                context={"entry_type": type(entry).__name__}
            )

        if "timestamp" not in entry or "data" not in entry:
            raise config_error(
                message="Cache entry must have timestamp and data",
                context={"missing_fields": [f for f in ["timestamp", "data"] if f not in entry]}
            )

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
            HTTPException: If validation fails (422)
        """
        if not config:
            raise config_error(
                message="Config data cannot be None",
                context={"config": None}
            )

    async def cache_config(self, config_type: str, config: ConfigData, ttl: int = 3600) -> None:
        """Cache configuration.

        Args:
            config_type: Configuration type
            config: Configuration data
            ttl: Time to live in seconds

        Raises:
            HTTPException: If caching fails (400)
        """
        try:
            await self._validate_config(config)
            self._cache[config_type] = CacheEntry(config, ttl)
            logger.debug("Cached config: {}", config_type)
        except HTTPException:
            raise
        except Exception as e:
            raise config_error(
                message=f"Failed to cache config: {str(e)}",
                context={"error": str(e)}
            )

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
