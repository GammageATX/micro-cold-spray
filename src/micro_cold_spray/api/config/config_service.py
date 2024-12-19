"""Configuration service module."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

from loguru import logger

from micro_cold_spray.api.base import ConfigurableService
from micro_cold_spray.api.base.base_exceptions import ConfigError, ValidationError
from micro_cold_spray.api.config.models import (
    ConfigData,
    ConfigMetadata,
    ConfigUpdate,
    TagRemapRequest,
    ConfigValidationResult,
    ConfigFieldInfo,
    SchemaRegistry
)

from micro_cold_spray.api.config.services import (
    ConfigCacheService,
    ConfigFileService,
    ConfigFormatService,
    ConfigRegistryService,
    ConfigSchemaService
)


class ConfigService(ConfigurableService):
    """Service for managing configuration files."""

    def __init__(self):
        """Initialize configuration service."""
        super().__init__()
        self._service_name = "config"
        self._version = "1.0.0"
        
        # Initialize services
        self._cache_service = ConfigCacheService()
        self._file_service = ConfigFileService(Path("config"))
        self._schema_service = ConfigSchemaService(Path("config/schemas"))
        self._registry_service = ConfigRegistryService()
        self._format_service = ConfigFormatService()
        
        # State tracking
        self._last_error = None
        self._last_update = datetime.now()
        self._schema_loaded = False

    async def _start(self) -> None:
        """Start configuration service."""
        try:
            logger.info("Starting configuration service...")
            
            # Start all services
            await self._cache_service.start()
            await self._file_service.start()
            await self._schema_service.start()
            await self._registry_service.start()
            await self._format_service.start()
            
            logger.info("Configuration service started successfully")
            
        except Exception as e:
            self._last_error = str(e)
            raise ConfigError("Failed to start configuration service", {"error": str(e)})

    async def _stop(self) -> None:
        """Stop configuration service."""
        try:
            logger.info("Stopping configuration service...")
            
            # Stop all services
            await self._cache_service.stop()
            await self._file_service.stop()
            await self._schema_service.stop()
            await self._registry_service.stop()
            await self._format_service.stop()
            
            logger.info("Configuration service stopped successfully")
            
        except Exception as e:
            self._last_error = str(e)
            raise ConfigError("Failed to stop configuration service", {"error": str(e)})

    async def get_config(self, config_type: str) -> ConfigData:
        """Get configuration data.
        
        Args:
            config_type: Type of configuration to get
        
        Returns:
            ConfigData: Configuration data
        
        Raises:
            ConfigError: If configuration cannot be retrieved
        """
        try:
            # Check cache first
            cached = await self._cache_service.get_cached_config(config_type)
            if cached:
                return cached
            
            # Load from file if not cached
            config = await self._file_service.load_config(config_type)
            if not config:
                raise ConfigError(f"Configuration not found: {config_type}")
            
            # Cache loaded config
            await self._cache_service.cache_config(config_type, config)
            return config
            
        except Exception as e:
            self._last_error = str(e)
            raise ConfigError(f"Failed to get configuration: {config_type}", {"error": str(e)})

    async def update_config(self, update: ConfigUpdate) -> ConfigValidationResult:
        """Update configuration data.
        
        Args:
            update: Configuration update request
        
        Returns:
            ConfigValidationResult: Validation result
        
        Raises:
            ConfigError: If configuration cannot be updated
        """
        try:
            # Validate config type
            if not update.config_type:
                raise ConfigError("Configuration type not specified")
            
            # Create config data
            config = ConfigData(
                metadata=ConfigMetadata(
                    config_type=update.config_type,
                    last_modified=datetime.now(),
                    version=self._version
                ),
                data=update.data
            )
            
            # Validate if requested
            if update.should_validate:
                errors = self._schema_service.validate_config(update.config_type, update.data)
                if errors:
                    return ConfigValidationResult(
                        valid=False,
                        errors=errors
                    )
            
            # Create backup if requested
            if update.backup:
                await self._file_service.create_backup(update.config_type)
            
            # Save config
            await self._file_service.save_config(update.config_type, config)
            
            # Update cache
            await self._cache_service.cache_config(update.config_type, config)
            
            # Update timestamp
            self._last_update = datetime.now()
            
            return ConfigValidationResult(valid=True)
            
        except Exception as e:
            self._last_error = str(e)
            raise ConfigError("Failed to update configuration", {"error": str(e)})

    async def check_health(self) -> Dict[str, Any]:
        """Check service health status."""
        try:
            # Check if all required services are running
            services_status = {
                "cache": self._cache_service.is_running,
                "file": self._file_service.is_running,
                "schema": self._schema_service.is_running,
                "registry": self._registry_service.is_running,
                "format": self._format_service.is_running
            }
            
            # Check if schema registry is loaded
            schema_loaded = self._schema_registry is not None
            
            # Determine overall status
            all_services_running = all(services_status.values())
            status = "ok" if all_services_running and schema_loaded else "error"
            
            return {
                "status": status,
                "service_info": {
                    "name": self.service_name,
                    "running": self.is_running,
                    "services": services_status,
                    "schema_loaded": schema_loaded,
                    "last_error": self._last_error,
                    "last_update": self._last_update.isoformat() if self._last_update else None,
                    "metrics": self.metrics
                }
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise ConfigError("Health check failed") from e

    async def validate_config(
        self, config_type: str, config_data: Dict[str, Any]
    ) -> ConfigValidationResult:
        """Validate configuration data."""
        try:
            if not self._schema_registry:
                raise ConfigError("Schema registry not initialized")

            schema = getattr(self._schema_registry, config_type, None)
            if not schema:
                raise ConfigError(f"Unknown config type: {config_type}")

            errors = self._schema_service.validate_config(config_type, config_data)
            return ConfigValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=[]
            )

        except Exception as e:
            logger.error(f"Failed to validate config {config_type}: {e}")
            raise ConfigError(f"Failed to validate config {config_type}") from e

    async def reload_config(self) -> None:
        """Reload configuration from disk."""
        try:
            # Clear cache
            await self._cache_service.clear_cache()
            
            # Reload schemas
            await self._schema_service.start()
            
            # Update state
            self._last_update = datetime.now()
            
            logger.info("Configuration reloaded successfully")
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Failed to reload configuration: {e}")
            raise ConfigError("Failed to reload configuration") from e

    async def get_editable_fields(
        self, config_type: str
    ) -> List[ConfigFieldInfo]:
        """Get list of editable fields for a config type.
        
        Args:
            config_type: Type of configuration
            
        Returns:
            List of field information
        """
        try:
            if not self._schema_registry:
                raise ConfigError("Schema registry not initialized")

            schema = getattr(self._schema_registry, config_type, None)
            if not schema:
                raise ConfigError(f"Unknown config type: {config_type}")

            config_data = await self.get_config(config_type)
            
            return await self._schema_service.get_editable_fields(
                schema, config_data.data
            )

        except Exception as e:
            logger.error(f"Failed to get editable fields for {config_type}: {e}")
            raise ConfigError(
                f"Failed to get editable fields for {config_type}"
            ) from e

    async def remap_tag(self, request: TagRemapRequest) -> None:
        """Remap a tag reference in all configs.
        
        Args:
            request: Tag remapping request
        """
        try:
            # Validate new tag if requested
            if request.validate:
                if not await self._registry_service.validate_tag(request.new_tag):
                    raise ConfigError(f"Invalid tag: {request.new_tag}")

            # Update all configs
            for config_type in self._schema_registry.model_fields:
                config_data = await self.get_config(config_type)
                updated = await self._registry_service.update_tag_references(
                    config_data.data, request.old_tag, request.new_tag
                )
                if updated:
                    await self.update_config(ConfigUpdate(
                        config_type=config_type,
                        data=config_data.data,
                        validate=request.validate
                    ))

        except ConfigError as e:
            logger.error(f"Failed to remap tag {request.old_tag}: {e}")
            raise  # Re-raise the original error
        except Exception as e:
            logger.error(f"Failed to remap tag {request.old_tag}: {e}")
            raise ConfigError(f"Failed to remap tag {request.old_tag}") from e

    async def clear_cache(self) -> None:
        """Clear the configuration cache."""
        try:
            await self._cache_service.clear_cache()
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise ConfigError("Failed to clear cache") from e
