"""Base configurable service class."""

from typing import Any, Dict
from loguru import logger

from micro_cold_spray.core.base.services.base_service import BaseService
from micro_cold_spray.core.config.service import ConfigService
from micro_cold_spray.core.config.models.config_types import ConfigType


class ConfigurableService(BaseService):
    """Base class for services that need configuration access."""

    def __init__(self, service_name: str, config_service: ConfigService = None):
        """Initialize configurable service.
        
        Args:
            service_name: Name of the service
            config_service: Optional ConfigService instance to use
        """
        super().__init__(service_name=service_name)
        self._config_service = config_service or ConfigService()
        self._config_cache: Dict[str, Any] = {}

    async def _get_system_config(self, key: str) -> Any:
        """Get system configuration value.
        
        Args:
            key: Configuration key (e.g. 'hardware.nozzle.type')
            
        Returns:
            Configuration value
        """
        if key not in self._config_cache:
            config = await self._config_service.get_config(ConfigType.APPLICATION)
            self._config_cache[key] = self._get_nested_value(config.data, key)
        return self._config_cache[key]

    async def _get_hardware_config(self, key: str) -> Any:
        """Get hardware configuration value.
        
        Args:
            key: Configuration key (e.g. 'nozzle.dimensions')
            
        Returns:
            Configuration value
        """
        if key not in self._config_cache:
            config = await self._config_service.get_config(ConfigType.HARDWARE)
            self._config_cache[key] = self._get_nested_value(config.data, key)
        return self._config_cache[key]

    async def _get_process_config(self, section: str, key: str) -> Any:
        """Get process configuration value.
        
        Args:
            section: Process section ('process', 'actions', 'validations')
            key: Configuration key
            
        Returns:
            Configuration value
        """
        cache_key = f"process.{section}.{key}"
        if cache_key not in self._config_cache:
            config = await self._config_service.get_config(ConfigType.PROCESS)
            self._config_cache[cache_key] = self._get_nested_value(config.data[section], key)
        return self._config_cache[cache_key]

    async def _get_state_config(self, key: str) -> Any:
        """Get state configuration value.
        
        Args:
            key: Configuration key (e.g. 'transitions.READY')
            
        Returns:
            Configuration value
        """
        if key not in self._config_cache:
            config = await self._config_service.get_config(ConfigType.STATE)
            self._config_cache[key] = self._get_nested_value(config.data, key)
        return self._config_cache[key]

    async def _get_tag_config(self, category: str, key: str) -> Any:
        """Get PLC tag configuration value.
        
        Args:
            category: Tag category ('control', 'hardware', 'system')
            key: Tag key
            
        Returns:
            Configuration value
        """
        cache_key = f"tags.{category}.{key}"
        if cache_key not in self._config_cache:
            config = await self._config_service.get_config(ConfigType.TAGS)
            self._config_cache[cache_key] = self._get_nested_value(config.data[category], key)
        return self._config_cache[cache_key]

    async def _get_communication_config(self, section: str) -> Any:
        """Get communication configuration value.
        
        Args:
            section: Configuration section ('network', 'clients', 'tags')
            
        Returns:
            Configuration value
        """
        cache_key = f"communication.{section}"
        if cache_key not in self._config_cache:
            config = await self._config_service.get_config(ConfigType.HARDWARE)
            if section in config.data:
                self._config_cache[cache_key] = config.data[section]
        return self._config_cache.get(cache_key)

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """Get nested dictionary value using dot notation.
        
        Args:
            data: Dictionary to search
            key: Dot-notation key (e.g. 'a.b.c')
            
        Returns:
            Value at key path
        """
        current = data
        for part in key.split('.'):
            if not isinstance(current, dict):
                return None
            if part not in current:
                return None
            current = current[part]
        return current

    async def _clear_config_cache(self) -> None:
        """Clear the configuration cache."""
        self._config_cache.clear()
        logger.debug(f"Cleared config cache for service {self.service_name}")

    async def _start(self) -> None:
        """Start the service."""
        await self._clear_config_cache()
        await super()._start()

    async def _stop(self) -> None:
        """Stop the service."""
        await self._clear_config_cache()
        await super()._stop()
