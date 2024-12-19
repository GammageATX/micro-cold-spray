"""Configuration registry service implementation."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type

from loguru import logger

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import ConfigError
from micro_cold_spray.api.config.models.config_models import ConfigData, ConfigMetadata


class ConfigRegistryService(BaseService):
    """Configuration registry service implementation."""

    def __init__(self, service_name: str) -> None:
        """Initialize service.

        Args:
            service_name: Service name
        """
        super().__init__(service_name)
        self._config_types: Dict[str, Type[ConfigData]] = {}
        self._configs: Dict[str, ConfigData] = {}

    async def _start(self) -> None:
        """Start registry service."""
        try:
            self._config_types.clear()
            self._configs.clear()
            logger.info("Registry service started")
        except Exception as e:
            raise ConfigError("Failed to start registry service", {"error": str(e)})

    def register_config_type(self, config_type: Type[ConfigData]) -> None:
        """Register configuration type.

        Args:
            config_type: Configuration type to register

        Raises:
            ConfigError: If type already exists
        """
        if config_type.__name__ in self._config_types:
            raise ConfigError(f"Config type {config_type.__name__} already registered")

        self._config_types[config_type.__name__] = config_type
        logger.info("Registered config type: {}", config_type.__name__)

    def get_config_type(self, type_name: str) -> Optional[Type[ConfigData]]:
        """Get configuration type by name.

        Args:
            type_name: Configuration type name

        Returns:
            Configuration type if found
        """
        return self._config_types.get(type_name)

    def get_config_types(self) -> List[str]:
        """Get registered configuration types.

        Returns:
            List of registered configuration types
        """
        return list(self._config_types.keys())

    async def register_config(self, config: ConfigData) -> None:
        """Register configuration.

        Args:
            config: Configuration data

        Raises:
            ConfigError: If registration fails
        """
        if not config.metadata.config_type:
            raise ConfigError("Config type not specified")

        if config.metadata.config_type not in self._config_types:
            raise ConfigError(f"Config type {config.metadata.config_type} not registered")

        try:
            self._configs[config.metadata.config_type] = config
            logger.info("Registered config: {}", config.metadata.config_type)
        except Exception as e:
            raise ConfigError("Failed to register config", {"error": str(e)})

    async def get_config(self, config_type: str) -> Optional[ConfigData]:
        """Get configuration by type.

        Args:
            config_type: Configuration type

        Returns:
            Configuration data if found
        """
        return self._configs.get(config_type)

    async def update_config(self, config: ConfigData) -> None:
        """Update configuration.

        Args:
            config: Configuration data

        Raises:
            ConfigError: If update fails
        """
        if not config.metadata.config_type:
            raise ConfigError("Config type not specified")

        if config.metadata.config_type not in self._config_types:
            raise ConfigError(f"Config type {config.metadata.config_type} not registered")

        try:
            config.metadata.last_modified = datetime.now()
            self._configs[config.metadata.config_type] = config
            logger.info("Updated config: {}", config.metadata.config_type)
        except Exception as e:
            raise ConfigError("Failed to update config", {"error": str(e)})

    async def delete_config(self, config_type: str) -> None:
        """Delete configuration.

        Args:
            config_type: Configuration type

        Raises:
            ConfigError: If delete fails
        """
        if config_type not in self._configs:
            raise ConfigError(f"Config {config_type} not found")

        try:
            del self._configs[config_type]
            logger.info("Deleted config: {}", config_type)
        except Exception as e:
            raise ConfigError("Failed to delete config", {"error": str(e)})

    async def check_health(self) -> dict:
        """Check service health.

        Returns:
            Health check result
        """
        health = await super().check_health()
        health["service_info"].update({
            "config_types": list(self._config_types.keys()),
            "configs": list(self._configs.keys())
        })
        return health
