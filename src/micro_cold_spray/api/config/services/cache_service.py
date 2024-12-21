"""Configuration cache service implementation."""

from typing import Dict, Union, Optional
from datetime import datetime, timedelta
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.services.base_config_service import BaseConfigService


class CacheEntry:
    """Cache entry with expiration."""

    def __init__(self, value: any, ttl: int = 300):
        """Initialize cache entry.
        
        Args:
            value: Cached value
            ttl: Time to live in seconds
        """
        self.value = value
        self.created = datetime.now()
        self.expires = self.created + timedelta(seconds=ttl)

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return datetime.now() > self.expires


class CacheService(BaseConfigService):
    """Configuration cache service implementation."""

    def __init__(self):
        """Initialize service."""
        super().__init__(name="cache")
        self._cache: Dict[str, Union[CacheEntry, Dict]] = {}

    async def _start(self) -> None:
        """Start implementation."""
        self._cache.clear()
        logger.info("Cache cleared on start")

    async def _stop(self) -> None:
        """Stop implementation."""
        self._cache.clear()
        logger.info("Cache cleared on stop")

    def get(self, key: str) -> Optional[any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[any]: Cached value if found and not expired
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Cache service not running"
            )

        entry = self._cache.get(key)
        if not entry:
            return None

        if isinstance(entry, CacheEntry) and entry.is_expired():
            del self._cache[key]
            return None

        return entry.value if isinstance(entry, CacheEntry) else entry

    def set(self, key: str, value: any, ttl: int = 300) -> None:
        """Set cache value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Cache service not running"
            )

        self._cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> None:
        """Delete cache entry.
        
        Args:
            key: Cache key
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Cache service not running"
            )

        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries.
        
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Cache service not running"
            )

        self._cache.clear()

    async def health(self) -> dict:
        """Get service health status."""
        health = await super().health()
        health.update({
            "cache_size": len(self._cache)
        })
        return health
