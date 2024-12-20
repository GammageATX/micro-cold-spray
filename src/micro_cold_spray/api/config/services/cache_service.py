"""Configuration cache service implementation."""

from typing import Dict, Union, Optional
from datetime import datetime
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.models.config_models import ConfigData


class CacheEntry:
    """Cache entry with TTL."""

    def __init__(self, data: ConfigData, ttl: int):
        """Initialize cache entry.
        
        Args:
            data: Configuration data
            ttl: Time to live in seconds
        """
        self.data = data
        self.ttl = ttl
        self.timestamp = datetime.now()

    def is_expired(self) -> bool:
        """Check if entry is expired.
        
        Returns:
            True if expired
        """
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl


class ConfigCacheService(BaseService):
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

    async def _validate_config(self, config: ConfigData) -> None:
        """Validate configuration.
        
        Args:
            config: Configuration data
            
        Raises:
            HTTPException: If validation fails (422)
        """
        if not config:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )
            
        try:
            await self._validate_config(config)
            self._cache[config_type] = CacheEntry(config, ttl)
            logger.debug(f"Cached config: {config_type}")
        except Exception as e:
            logger.error(f"Failed to cache config: {e}")
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Failed to cache config",
                context={"error": str(e)},
                cause=e
            )

    async def get_config(self, config_type: str) -> Optional[ConfigData]:
        """Get cached configuration.
        
        Args:
            config_type: Configuration type
            
        Returns:
            Configuration data if found and not expired
            
        Raises:
            HTTPException: If service not running (503)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )
            
        try:
            entry = self._cache.get(config_type)
            if not entry:
                return None
                
            if isinstance(entry, CacheEntry) and entry.is_expired():
                del self._cache[config_type]
                return None
                
            return entry.data if isinstance(entry, CacheEntry) else entry
            
        except Exception as e:
            logger.error(f"Failed to get cached config: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to get cached config",
                context={"error": str(e)},
                cause=e
            )

    async def clear_cache(self) -> None:
        """Clear cache.
        
        Raises:
            HTTPException: If service not running (503)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )
            
        self._cache.clear()
        logger.info("Cache cleared")

    async def health(self) -> dict:
        """Get service health status.
        
        Returns:
            Health check result
        """
        health = await super().health()
        health["context"].update({
            "cache_size": len(self._cache)
        })
        return health
