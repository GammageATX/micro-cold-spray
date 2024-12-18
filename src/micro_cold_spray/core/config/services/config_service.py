"""Configuration service implementation."""

from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from pathlib import Path

from loguru import logger

from micro_cold_spray.core.base import BaseService
from micro_cold_spray.core.errors import (
    AppErrorCode, raise_http_error,
    ConfigurationError, ValidationError
)
from micro_cold_spray.core.config.models import (
    ConfigData, ConfigUpdate,
    ConfigValidationResult, ConfigMetadata,
    ConfigFieldInfo, TagRemapRequest
)

from .cache_service import ConfigCacheService
from ..repositories.config_repository import ConfigRepository
from .format_service import FormatService
from .registry_service import RegistryService
from .schema_service import SchemaService


class ConfigService(BaseService):
    """Service for managing configuration files."""

    def __init__(self):
        """Initialize config service."""
        super().__init__(service_name="config")
        
        # Use simple hardcoded paths relative to current directory
        self._config_dir = Path("config")
        self._schema_dir = self._config_dir / "schemas"
        self._backup_dir = self._config_dir / "backups"
        
        # Initialize services
        self._cache_service = ConfigCacheService()
        self._config_repository = ConfigRepository(self._config_dir, self._backup_dir)
        self._schema_service = SchemaService(self._schema_dir)
        self._registry_service = RegistryService()
        self._format_service = FormatService()
        
        # State tracking
        self._last_error: Optional[str] = None
        self._last_update: Optional[datetime] = None
        self._known_tags: Set[str] = set()

    async def _start(self) -> None:
        """Start the configuration service."""
        try:
            # Initialize services first
            await self._cache_service.start()
            await self._schema_service.start()
            await self._registry_service.start()
            await self._format_service.start()

            # Check if required schemas are loaded
            required_schemas = {"application", "hardware", "process", "tags", "state", "file_format"}
            loaded_schemas = set(self._schema_service._schemas.keys())
            missing_schemas = required_schemas - loaded_schemas
            
            if missing_schemas:
                raise ConfigurationError(f"Missing required schemas: {', '.join(missing_schemas)}")

            logger.info("Configuration service started successfully")

        except ConfigurationError as e:
            logger.error(f"Failed to start configuration service: {e}")
            self._error = str(e)
            raise_http_error(
                AppErrorCode.SERVICE_UNAVAILABLE,
                str(e),
                e.context
            )
        except Exception as e:
            logger.error(f"Failed to start configuration service: {e}")
            self._error = str(e)
            raise_http_error(
                AppErrorCode.SERVICE_ERROR,
                f"Internal error: {str(e)}"
            )

    async def _stop(self) -> None:
        """Stop the configuration service."""
        try:
            await self._cache_service.stop()
            await self._schema_service.stop()
            await self._registry_service.stop()
            await self._format_service.stop()
            logger.info("Configuration service stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop configuration service: {e}")
            self._error = str(e)
            raise_http_error(
                AppErrorCode.SERVICE_ERROR,
                f"Failed to stop service: {str(e)}"
            )

    async def _check_health(self) -> Dict[str, Any]:
        """Check service health status."""
        try:
            # Check if all required services are running and ready
            services_status = {}
            try:
                services_status["cache"] = await self._cache_service.check_health()
            except Exception as e:
                services_status["cache"] = {"status": "error", "error": str(e)}
                
            try:
                services_status["schema"] = await self._schema_service.check_health()
            except Exception as e:
                services_status["schema"] = {"status": "error", "error": str(e)}
                
            try:
                services_status["registry"] = await self._registry_service.check_health()
            except Exception as e:
                services_status["registry"] = {"status": "error", "error": str(e)}
                
            try:
                services_status["format"] = await self._format_service.check_health()
            except Exception as e:
                services_status["format"] = {"status": "error", "error": str(e)}
            
            # Check if all required schemas are loaded
            required_schemas = {"application", "hardware", "process", "tags", "state", "file_format"}
            loaded_schemas = set(self._schema_service._schemas.keys())
            missing_schemas = required_schemas - loaded_schemas
            
            # Determine overall status
            all_services_running = all(
                service.get("status", "error") == "ok"
                for service in services_status.values()
            )
            
            # Service is ready only if all conditions are met
            is_ready = all_services_running and not missing_schemas
            status_str = "ok" if is_ready else "not_ready"
            
            # Build detailed health response
            health_info = {
                "status": status_str,
                "is_ready": is_ready,
                "service_info": {
                    "ready": is_ready,
                    "version": "1.0.0",
                    "uptime": self.uptime
                },
                "services": services_status,
                "schema_loaded": bool(loaded_schemas),
                "missing_schemas": list(missing_schemas) if missing_schemas else None,
                "last_error": self._last_error,
                "last_update": self._last_update.isoformat() if self._last_update else None
            }
            
            # If not ready, include more details
            if not is_ready:
                health_info["message"] = "Service is starting"
                if not all_services_running:
                    failing_services = [
                        name for name, status in services_status.items()
                        if status.get("status", "error") != "ok"
                    ]
                    health_info["message"] = f"Waiting for services: {', '.join(failing_services)}"
                elif missing_schemas:
                    health_info["message"] = f"Missing required schemas: {', '.join(missing_schemas)}"
            
            return health_info
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "is_ready": False,
                "service_info": {
                    "ready": False,
                    "version": "1.0.0",
                    "uptime": self.uptime
                },
                "error": str(e)
            }

    async def get_config(self, config_type: str) -> ConfigData:
        """Get configuration data."""
        try:
            logger.debug(f"Loading config type: {config_type}")
            
            # Check cache first
            cached_data = await self._cache_service.get_cached_config(config_type)
            if cached_data:
                logger.debug(f"Found cached config for {config_type}")
                return cached_data

            # Load from repository if not cached
            config_data = await self._config_repository.load_config(config_type)
            logger.debug(f"Loaded config data: {config_data.data.keys()}")
            
            # Cache the loaded data
            await self._cache_service.cache_config(config_type, config_data)
            
            return config_data

        except ConfigurationError as e:
            logger.error(f"Failed to get config {config_type}: {e}")
            raise_http_error(
                AppErrorCode.RESOURCE_NOT_FOUND,
                f"Configuration not found: {config_type}",
                e.context
            )
        except Exception as e:
            logger.error(f"Failed to get config {config_type}: {e}")
            raise_http_error(
                AppErrorCode.SERVICE_ERROR,
                f"Failed to get configuration: {str(e)}"
            )

    async def update_config(self, update: ConfigUpdate) -> ConfigValidationResult:
        """Update configuration data.
        
        Args:
            update: Configuration update request
            
        Returns:
            Validation result
        """
        try:
            # Validate update if requested
            if update.should_validate:
                validation_result = await self.validate_config(
                    update.config_type, update.data
                )
                if not validation_result.valid:
                    raise ValidationError(
                        "Configuration validation failed",
                        {"errors": validation_result.errors}
                    )

            # Save config with the correct parameters
            await self._config_repository.save_config(
                config_type=update.config_type,
                data=update.data,
                create_backup=update.backup
            )
            
            # Create config data object for cache
            config_data = ConfigData(
                metadata=ConfigMetadata(
                    config_type=update.config_type,
                    last_modified=datetime.now()
                ),
                data=update.data.get(update.config_type, update.data)  # Try to unwrap, fallback to raw data
            )
            
            # Update cache
            await self._cache_service.cache_config(update.config_type, config_data)

            return ConfigValidationResult(valid=True, errors=[], warnings=[])

        except ValidationError as e:
            logger.error(f"Validation failed for config {update.config_type}: {e}")
            raise_http_error(
                AppErrorCode.VALIDATION_ERROR,
                str(e),
                e.context
            )
        except ConfigurationError as e:
            logger.error(f"Failed to update config {update.config_type}: {e}")
            raise_http_error(
                AppErrorCode.INVALID_REQUEST,
                str(e),
                e.context
            )
        except Exception as e:
            logger.error(f"Failed to update config {update.config_type}: {e}")
            raise_http_error(
                AppErrorCode.SERVICE_ERROR,
                f"Failed to update configuration: {str(e)}"
            )

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
            if not self._schema_service:
                raise ConfigurationError("Schema service not initialized")

            # Get schema from schema service
            schema = self._schema_service.get_schema(config_type)
            if not schema:
                raise ConfigurationError(
                    f"Unknown config type: {config_type}",
                    {"available_types": list(self._schema_service._schemas.keys())}
                )

            errors = await self._schema_service.validate_config(config_type, config_data)
            return ConfigValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=[]
            )

        except ConfigurationError as e:
            logger.error(f"Failed to validate config {config_type}: {e}")
            raise_http_error(
                AppErrorCode.INVALID_REQUEST,
                str(e),
                e.context
            )
        except Exception as e:
            logger.error(f"Failed to validate config {config_type}: {e}")
            raise_http_error(
                AppErrorCode.SERVICE_ERROR,
                f"Failed to validate configuration: {str(e)}"
            )

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
            if not self._schema_service:
                raise ConfigurationError("Schema service not initialized")

            # Get schema from schema service
            schema = self._schema_service.get_schema(config_type)
            if not schema:
                raise ConfigurationError(
                    f"Unknown config type: {config_type}",
                    {"available_types": list(self._schema_service._schemas.keys())}
                )

            config_data = await self.get_config(config_type)
            
            return await self._schema_service.get_editable_fields(
                schema, config_data.data
            )

        except ConfigurationError as e:
            logger.error(f"Failed to get editable fields for {config_type}: {e}")
            raise_http_error(
                AppErrorCode.INVALID_REQUEST,
                str(e),
                e.context
            )
        except Exception as e:
            logger.error(f"Failed to get editable fields for {config_type}: {e}")
            raise_http_error(
                AppErrorCode.SERVICE_ERROR,
                f"Failed to get editable fields: {str(e)}"
            )

    async def remap_tag(self, request: TagRemapRequest) -> None:
        """Remap a tag reference in all configs.
        
        Args:
            request: Tag remapping request
        """
        try:
            # Validate new tag if requested
            if request.should_validate:
                if not await self._registry_service.validate_tag(request.new_tag):
                    raise ValidationError(
                        f"Invalid tag: {request.new_tag}",
                        {"tag": request.new_tag}
                    )

            # Update all configs
            for config_type in self._schema_service._schemas.keys():
                config_data = await self.get_config(config_type)
                updated = await self._registry_service.update_tag_references(
                    config_data.data, request.old_tag, request.new_tag
                )
                if updated:
                    await self.update_config(ConfigUpdate(
                        config_type=config_type,
                        data=config_data.data,
                        should_validate=request.should_validate
                    ))

        except ConfigurationError as e:
            logger.error(f"Failed to remap tag {request.old_tag}: {e}")
            raise_http_error(
                AppErrorCode.INVALID_REQUEST,
                str(e),
                e.context
            )
        except Exception as e:
            logger.error(f"Failed to remap tag {request.old_tag}: {e}")
            raise_http_error(
                AppErrorCode.SERVICE_ERROR,
                f"Failed to remap tag: {str(e)}"
            )

    async def clear_cache(self) -> None:
        """Clear the configuration cache."""
        try:
            await self._cache_service.clear_cache()
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise_http_error(
                AppErrorCode.SERVICE_ERROR,
                f"Failed to clear cache: {str(e)}"
            )
