"""Configuration cache service."""

from datetime import datetime
from typing import Dict, Optional, Any
from fastapi import status, HTTPException

from loguru import logger

from micro_cold_spray.core.base import BaseService
from micro_cold_spray.core.config.models import ConfigData


class CacheEntry:
    def __init__(self, data: ConfigData, ttl: int = 3600):
        if not data:
            raise ValueError("Config data cannot be None")
        if not data.metadata or not data.data:
            raise ValueError("Invalid config data")
        self.data = data
        self.timestamp = datetime.now()
        self.ttl = ttl


class ConfigCacheService(BaseService):
    """Service for caching configuration data."""

    def __init__(self):
        """Initialize cache service."""
        super().__init__(service_name="config_cache")
        self._cache: Dict[str, CacheEntry] = {}
        self._last_cleanup = datetime.now()

    async def _start(self) -> None:
        """Start the cache service."""
        try:
            self._cache = {}
            self._last_cleanup = datetime.now()
            logger.info("Cache service started successfully")
        except Exception as e:
            logger.error(f"Failed to start cache service: {e}")
            self._error = str(e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to start cache service: {str(e)}"
            )

    async def _stop(self) -> None:
        """Stop the cache service."""
        try:
            self._cache = {}
            self._last_cleanup = datetime.now()
            logger.info("Cache service stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop cache service: {e}")
            self._error = str(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stop cache service: {str(e)}"
            )

    async def _check_health(self) -> Dict[str, Any]:
        """Check cache service health."""
        return {
            "cache_size": len(self._cache),
            "last_cleanup": self._last_cleanup.isoformat()
        }

    async def get_cached_config(self, config_type: str) -> Optional[ConfigData]:
        """Get cached config with TTL check."""
        if config_type is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Config type cannot be None"
            )
        
        try:
            self._cleanup_expired()
            entry = self._cache.get(config_type)
            if entry and not self._is_expired(entry):
                return entry.data
            return None
        except Exception as e:
            logger.error(f"Failed to get cached config {config_type}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get cached config: {str(e)}"
            )

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        return (datetime.now() - entry.timestamp).total_seconds() > entry.ttl

    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = datetime.now()
        if (now - self._last_cleanup).total_seconds() > 60:
            self._cache = {
                k: v for k, v in self._cache.items()
                if not self._is_expired(v)
            }
            self._last_cleanup = now

    async def cache_config(self, config_type: str, config_data: ConfigData) -> None:
        """Cache configuration data.
        
        Args:
            config_type: Type of configuration to cache
            config_data: Configuration data to cache
            
        Raises:
            HTTPException: If caching fails
        """
        if config_type is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Config type cannot be None"
            )
        if config_data is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Config data cannot be None"
            )
            
        try:
            self._cache[config_type] = CacheEntry(config_data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to cache config {config_type}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cache config: {str(e)}"
            )

    async def clear_cache(self) -> None:
        """Clear all cached configurations."""
        try:
            self._cache.clear()
            self._last_cleanup = datetime.now()
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to clear cache: {str(e)}"
            )

    async def remove_from_cache(self, config_type: str) -> None:
        """Remove configuration from cache.
        
        Args:
            config_type: Type of configuration to remove
        """
        try:
            if config_type in self._cache:
                del self._cache[config_type]
        except Exception as e:
            logger.error(f"Failed to remove config {config_type} from cache: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to remove config from cache: {str(e)}"
            )

    @property
    def cache_size(self) -> int:
        """Get number of cached configurations."""
        return len(self._cache)

    @property
    def last_update(self) -> Optional[datetime]:
        """Get timestamp of last cache update."""
        return self._last_cleanup
