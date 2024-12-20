"""Configuration service implementation."""

from typing import Dict, Type, Optional
import threading
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.models.config_models import ConfigData


class ConfigService(BaseService):
    """Configuration service implementation."""
    
    _instance: Optional['ConfigService'] = None
    _lock = threading.Lock()
    
    def __new__(cls, service_name: str) -> 'ConfigService':
        """Create or return singleton instance.
        
        Args:
            service_name: Service name
            
        Returns:
            ConfigService instance
        """
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    instance = super().__new__(cls)
                    # Initialize base class
                    BaseService.__init__(instance, service_name)
                    # Set instance attributes
                    instance._config_types = {}
                    instance._config_cache = {}
                    cls._instance = instance
        return cls._instance

    def __init__(self, service_name: str) -> None:
        """Initialize service.
        
        Args:
            service_name: Service name
        """
        # Skip initialization if already initialized
        pass

    async def _start(self) -> None:
        """Start service implementation."""
        # Nothing special needed for startup
        pass

    async def _stop(self) -> None:
        """Stop service implementation."""
        # Clear caches on shutdown
        self._config_cache.clear()

    def register_config_type(self, config_type: Type[ConfigData]) -> None:
        """Register configuration type.
        
        Args:
            config_type: Configuration type to register
        """
        self._config_types[config_type.__name__] = config_type
        logger.info(f"Registered config type: {config_type.__name__}")

    def get_config_type(self, type_name: str) -> Type[ConfigData]:
        """Get configuration type by name.
        
        Args:
            type_name: Configuration type name
        
        Returns:
            Configuration type
        
        Raises:
            HTTPException: If type not found (404)
        """
        if type_name not in self._config_types:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Config type {type_name} not found",
                context={"type_name": type_name}
            )
        return self._config_types[type_name]

    async def get_config(self, config_type: str) -> ConfigData:
        """Get configuration.
        
        Args:
            config_type: Configuration type
            
        Returns:
            Configuration data
            
        Raises:
            HTTPException: If service not running (503) or config not found (404)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )

        if config_type not in self._config_types:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Config type {config_type} not found",
                context={"type_name": config_type}
            )

        if config_type not in self._config_cache:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"No configuration found for type {config_type}",
                context={"type_name": config_type}
            )

        return self._config_cache[config_type]

    async def update_config(self, config: ConfigData) -> None:
        """Update configuration.
        
        Args:
            config: Configuration data
            
        Raises:
            HTTPException: If service not running (503) or config type not found (404)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )

        if config.metadata.config_type not in self._config_types:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Config type {config.metadata.config_type} not found",
                context={"type_name": config.metadata.config_type}
            )

        self._config_cache[config.metadata.config_type] = config

    async def get_config_types(self) -> Dict[str, Type[ConfigData]]:
        """Get registered configuration types.
        
        Returns:
            Dictionary of registered configuration types
        """
        return self._config_types.copy()

    async def clear_cache(self) -> None:
        """Clear configuration cache."""
        self._config_cache.clear()

    async def check_health(self) -> dict:
        """Check service health.
        
        Returns:
            Health check result
        """
        health = await super().health()
        health["status"] = "ok" if self.is_running else "stopped"
        health["context"]["config_types"] = list(self._config_types.keys())
        return health
