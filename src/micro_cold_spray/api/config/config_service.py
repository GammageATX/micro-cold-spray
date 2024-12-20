"""Configuration service implementation."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Type
import threading

from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error, BaseError
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.config.models.config_models import ConfigData
from micro_cold_spray.api.config.services.cache_service import CacheService
from micro_cold_spray.api.config.services.file_service import FileService
from micro_cold_spray.api.config.services.registry_service import ConfigRegistryService


class ConfigService(BaseService):
    """Configuration service implementation."""

    _instance: Optional['ConfigService'] = None
    _lock = threading.Lock()

    def __new__(cls, config_dir: Optional[Path] = None) -> 'ConfigService':
        """Create or return singleton instance.
        
        Args:
            config_dir: Configuration directory path
            
        Returns:
            ConfigService: Singleton instance
        """
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration service.
        
        Args:
            config_dir: Configuration directory path
        """
        if not hasattr(self, '_initialized') or not self._initialized:
            super().__init__()
            self._config_dir = config_dir
            self._registry = ConfigRegistryService()
            self._file_service = FileService()
            self._cache_service = CacheService()
            self._start_time: Optional[datetime] = None
            self._initialized = True

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds.
        
        Returns:
            float: Service uptime in seconds
        """
        if not self._start_time:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    async def _start(self) -> None:
        """Start configuration service."""
        try:
            await self._registry.start()
            self._start_time = datetime.now()
            self._is_running = True
            logger.info("Config service started")
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to start config service",
                context={"error": str(e)},
                cause=e
            )

    async def _stop(self) -> None:
        """Stop configuration service."""
        try:
            await self._registry.stop()
            self._start_time = None
            self._is_running = False
            logger.info("Config service stopped")
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to stop config service",
                context={"error": str(e)},
                cause=e
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Dict[str, Any]: Health check response
        """
        try:
            registry_health = await self._registry.check_health()
            return {
                "status": "running" if self.is_running else "stopped",
                "is_healthy": self.is_running and registry_health["is_healthy"],
                "uptime": self.uptime,
                "context": {
                    "service": "config",
                    "config_dir": str(self._config_dir) if self._config_dir else None,
                    "registry": registry_health["context"]
                }
            }
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to check config service health",
                context={"error": str(e)},
                cause=e
            )

    async def get_config(self, config_id: str) -> ConfigData:
        """Get configuration by ID.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            ConfigData: Configuration data
            
        Raises:
            HTTPException: If config not found (404) or service error (503)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Config service is not running"
            )

        try:
            # Try cache first
            cached = await self._cache_service.get_config(config_id)
            if cached:
                return cached

            # Load from file
            config = await self._file_service.load_config(config_id)
            if not config:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Config {config_id} not found"
                )

            # Cache for next time
            await self._cache_service.set_config(config_id, config)
            return config

        except Exception as e:
            if isinstance(e, BaseError):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get config",
                context={"config_id": config_id, "error": str(e)},
                cause=e
            )

    async def register_config_type(self, config_type: Type[ConfigData]) -> None:
        """Register configuration type.
        
        Args:
            config_type: Configuration type to register
            
        Raises:
            HTTPException: If service not running (503) or type already exists (409)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Config service is not running"
            )

        try:
            await self._registry.register_config_type(config_type)
        except Exception as e:
            if isinstance(e, BaseError):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to register config type",
                context={"type": config_type.__name__, "error": str(e)},
                cause=e
            )
