"""Configuration service implementation."""

from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from pathlib import Path

from loguru import logger

from micro_cold_spray.api.base import BaseService
from micro_cold_spray.api.config.models import (
    SchemaRegistry, ConfigData, ConfigUpdate,
    ConfigValidationResult, ConfigMetadata,
    ConfigFieldInfo, TagRemapRequest
)
from micro_cold_spray.api.config.services import (
    SchemaService, RegistryService, ConfigFileService,
    ConfigCacheService, FormatService
)
from micro_cold_spray.api.base.exceptions import ConfigurationError


class ConfigService(BaseService):
    """Service for managing configuration files."""

    def __init__(self):
        """Initialize config service."""
        super().__init__(service_name="config")
        
        # Use simple hardcoded paths relative to current directory
        self._config_dir = Path("config")
        self._schema_dir = self._config_dir / "schemas"
        
        # Initialize services
        self._cache_service = ConfigCacheService()
        self._file_service = ConfigFileService(self._config_dir)
        self._schema_service = SchemaService(self._schema_dir)
        self._registry_service = RegistryService()
        self._format_service = FormatService()
        
        # State tracking
        self._last_error: Optional[str] = None
        self._last_update: Optional[datetime] = None
        self._known_tags: Set[str] = set()
        self._schema_registry: Optional[SchemaRegistry] = None

    async def _start(self) -> None:
        """Start the configuration service."""
        try:
            # Initialize services first
            await self._cache_service.start()
            await self._file_service.start()
            await self._schema_service.start()
            await self._registry_service.start()
            await self._format_service.start()

            # Get schemas from schema service
            self._schema_registry = SchemaRegistry(
                application=self._schema_service.get_schema("application"),
                hardware=self._schema_service.get_schema("hardware"),
                process=self._schema_service.get_schema("process"),
                tags=self._schema_service.get_schema("tags"),
                state=self._schema_service.get_schema("state"),
                file_format=self._schema_service.get_schema("file_format")
            )

            if not self._schema_registry:
                raise ConfigurationError("Failed to load schema registry")

            logger.info("Configuration service started successfully")

        except Exception as e:
            logger.error(f"Failed to start configuration service: {e}")
            raise

    async def _stop(self) -> None:
        """Stop the configuration service."""
        try:
            await self._cache_service.stop()
            await self._file_service.stop()
            await self._schema_service.stop()
            await self._registry_service.stop()
            await self._format_service.stop()
            logger.info("Configuration service stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop configuration service: {e}")
            raise

    async def get_config(self, config_type: str) -> ConfigData:
        """Get configuration data."""
        try:
            logger.debug(f"Loading config type: {config_type}")
            
            # Check cache first
            cached_data = await self._cache_service.get_cached_config(config_type)
            if cached_data:
                logger.debug(f"Found cached config for {config_type}")
                return cached_data

            # Load from file if not cached
            config_data = await self._file_service.load_config(config_type)
            logger.debug(f"Loaded config data: {config_data.data.keys()}")
            
            # Cache the loaded data
            await self._cache_service.cache_config(config_type, config_data)
            
            return config_data

        except Exception as e:
            logger.error(f"Failed to get config {config_type}: {e}")
            raise ConfigurationError(f"Failed to get config {config_type}") from e

    async def update_config(self, update: ConfigUpdate) -> ConfigValidationResult:
        """Update configuration data.
        
        Args:
            update: Configuration update request
            
        Returns:
            Validation result
        """
        try:
            # Validate update if requested
            if update.validate:
                validation_result = await self.validate_config(
                    update.config_type, update.data
                )
                if not validation_result.valid:
                    return validation_result

            # Create backup if requested
            if update.backup:
                await self._file_service.create_backup(update.config_type)

            # Create config data object
            config_data = ConfigData(
                metadata=ConfigMetadata(
                    config_type=update.config_type,
                    last_modified=datetime.now()
                ),
                data=update.data
            )

            # Save config
            await self._file_service.save_config(config_data)
            
            # Update cache
            await self._cache_service.cache_config(update.config_type, config_data)

            return ConfigValidationResult(valid=True, errors=[], warnings=[])

        except Exception as e:
            logger.error(f"Failed to update config {update.config_type}: {e}")
            raise ConfigurationError(f"Failed to update config {update.config_type}") from e

    async def validate_config(
        self, config_type: str, config_data: Dict[str, Any]
    ) -> ConfigValidationResult:
        """Validate configuration data against schema.
        
        Args:
            config_type: Type of configuration to validate
            config_data: Configuration data to validate
            
        Returns:
            Validation result
        """
        try:
            if not self._schema_registry:
                raise ConfigurationError("Schema registry not initialized")

            schema = getattr(self._schema_registry, config_type, None)
            if not schema:
                raise ConfigurationError(f"Unknown config type: {config_type}")

            errors = self._schema_service.validate_config(config_type, config_data)
            return ConfigValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=[]
            )

        except ConfigurationError as e:
            logger.error(f"Failed to validate config {config_type}: {e}")
            raise  # Re-raise the original error
        except Exception as e:
            logger.error(f"Failed to validate config {config_type}: {e}")
            raise ConfigurationError(f"Failed to validate config {config_type}") from e

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
                raise ConfigurationError("Schema registry not initialized")

            schema = getattr(self._schema_registry, config_type, None)
            if not schema:
                raise ConfigurationError(f"Unknown config type: {config_type}")

            config_data = await self.get_config(config_type)
            
            return await self._schema_service.get_editable_fields(
                schema, config_data.data
            )

        except Exception as e:
            logger.error(f"Failed to get editable fields for {config_type}: {e}")
            raise ConfigurationError(
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
                    raise ConfigurationError(f"Invalid tag: {request.new_tag}")

            # Update all configs
            for config_type in self._schema_registry.__fields__:
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

        except ConfigurationError as e:
            logger.error(f"Failed to remap tag {request.old_tag}: {e}")
            raise  # Re-raise the original error
        except Exception as e:
            logger.error(f"Failed to remap tag {request.old_tag}: {e}")
            raise ConfigurationError(f"Failed to remap tag {request.old_tag}") from e
