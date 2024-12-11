"""Configuration service implementation."""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from ..base import BaseService
from .models import ConfigUpdate, ConfigStatus
from .exceptions import ConfigurationError
from .services import ConfigCacheService, ConfigFileService

# Config directory - use workspace root config directory
CONFIG_DIR = Path(__file__).parents[4] / "config"


class ConfigService(BaseService):
    """Service for managing configuration files."""

    def __init__(self):
        """Initialize config service."""
        super().__init__(service_name="config")
        self._cache_service = ConfigCacheService()
        self._file_service = ConfigFileService(CONFIG_DIR)
        self._last_error: Optional[str] = None
        self._last_update: Optional[datetime] = None

    async def _start(self) -> None:
        """Start config service."""
        try:
            # Start component services
            await self._cache_service.start()
            await self._file_service.start()
            logger.info("Config service started")
        except Exception as e:
            error_msg = f"Failed to start config service: {str(e)}"
            self._last_error = error_msg
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    async def _stop(self) -> None:
        """Stop config service."""
        try:
            # Stop component services in reverse order
            await self._cache_service.stop()
            await self._file_service.stop()
            logger.info("Config service stopped")
        except Exception as e:
            error_msg = f"Failed to stop config service: {str(e)}"
            self._last_error = error_msg
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    async def get_config(self, config_type: str) -> Dict[str, Any]:
        """Get configuration by type.
        
        Args:
            config_type: Type of config to get (e.g. "hardware", "tags")
            
        Returns:
            Dict containing configuration data
            
        Raises:
            ConfigurationError: If config cannot be loaded or service not running
        """
        if not self.is_running:
            raise ConfigurationError(
                "Config service not running",
                {"config_type": config_type}
            )
            
        try:
            # Check if file exists
            if not self._file_service.config_exists(config_type):
                raise ConfigurationError(
                    f"Config file not found: {config_type}",
                    {"config_type": config_type}
                )
                
            # Get file timestamp
            file_timestamp = self._file_service.get_config_timestamp(config_type)
            
            # Return cached config if valid
            if self._cache_service.is_cache_valid(config_type, file_timestamp):
                config_data = self._cache_service.get_cached_config(config_type)
                if config_data:
                    return config_data.data
            
            # Load from file and update cache
            config_data = await self._file_service.load_config(config_type)
            self._cache_service.update_cache(config_type, config_data.data)
            
            return config_data.data
            
        except ConfigurationError:
            raise
        except Exception as e:
            error_msg = f"Failed to get config: {str(e)}"
            self._last_error = error_msg
            logger.error(error_msg)
            raise ConfigurationError(
                error_msg,
                {
                    "config_type": config_type,
                    "error": str(e)
                }
            )

    async def update_config(self, update: ConfigUpdate) -> None:
        """Update configuration.
        
        Args:
            update: Configuration update request
            
        Raises:
            ConfigurationError: If config cannot be updated or service not running
        """
        if not self.is_running:
            raise ConfigurationError(
                "Config service not running",
                {"config_type": update.config_type}
            )
            
        try:
            # Save to file
            await self._file_service.save_config(
                update.config_type,
                update.data,
                update.backup
            )
            
            # Update cache
            self._cache_service.update_cache(update.config_type, update.data)
            
            # Update status
            self._last_update = datetime.now()
            self._last_error = None
            
            logger.info(f"Updated config: {update.config_type}")
            
        except Exception as e:
            error_msg = f"Failed to update config: {str(e)}"
            self._last_error = error_msg
            logger.error(error_msg)
            raise ConfigurationError(
                error_msg,
                {
                    "config_type": update.config_type,
                    "error": str(e)
                }
            )

    def get_status(self) -> ConfigStatus:
        """Get service status.
        
        Returns:
            Current service status including running state, cache info, and errors
        """
        return ConfigStatus(
            is_running=self.is_running,
            cache_size=self._cache_service.cache_size,
            last_error=self._last_error,
            last_update=self._last_update
        )
