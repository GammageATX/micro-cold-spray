"""Configuration cache service implementation."""

from typing import Dict, Union, Optional
from datetime import datetime, timedelta
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error


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


class CacheService(BaseService):
    """Configuration cache service implementation."""

    def __init__(self, name: str = "cache"):
        """Initialize service.
        
        Args:
            name: Service name
        """
        super().__init__(name=name)
        self._cache: Dict[str, Union[CacheEntry, Dict]] = {}

    async def _start(self) -> None:
        """Start implementation."""
        try:
            await self._initialize()
            logger.info("Cache service started")
        except Exception as e:
            logger.error(f"Failed to start cache service: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to start cache service",
                context={"error": str(e)},
                cause=e
            )

    async def _stop(self) -> None:
        """Stop implementation."""
        try:
            await self._cleanup()
            logger.info("Cache service stopped")
        except Exception as e:
            logger.error(f"Failed to stop cache service: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to stop cache service",
                context={"error": str(e)},
                cause=e
            )

    async def _initialize(self) -> None:
        """Initialize cache."""
        self._cache.clear()

    async def _cleanup(self) -> None:
        """Clean up cache."""
        self._cache.clear()

    def get(self, key: str) -> Optional[any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[any]: Cached value if found and not expired
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
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
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )

        self._cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> None:
        """Delete cache entry.
        
        Args:
            key: Cache key
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )

        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )

        self._cache.clear()

    def get_size(self) -> int:
        """Get number of cache entries.
        
        Returns:
            int: Number of entries
        """
        return len(self._cache)
