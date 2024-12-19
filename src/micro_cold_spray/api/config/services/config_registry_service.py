"""Configuration registry service implementation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, Set, Any

from loguru import logger

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_exceptions import ConfigError, ValidationError
from micro_cold_spray.api.config.models.config_models import ConfigData, ConfigMetadata


class ValidationResult:
    """Validation result."""

    def __init__(self) -> None:
        """Initialize validation result."""
        self.valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []


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
        self._tags: Set[str] = set()
        self._actions: Set[str] = {"read", "write", "monitor"}
        self._validations: Set[str] = {"range", "enum", "pattern"}

    async def start(self) -> None:
        """Start service.

        Raises:
            ConfigError: If service fails to start
        """
        if self.is_running:
            return

        try:
            await self._start()
            self._is_running = True
            self._is_initialized = True
            self._start_time = datetime.now()
            self._metrics["start_count"] += 1
        except Exception as e:
            self._metrics["error_count"] += 1
            self._metrics["last_error"] = str(e)
            raise ConfigError("Failed to start registry service") from e

    async def _start(self) -> None:
        """Start registry service."""
        try:
            self._config_types.clear()
            self._configs.clear()
            await self._load_tag_registry()
            await self._load_action_registry()
            await self._load_validation_registry()
            logger.info("Registry service started")
        except Exception as e:
            raise ConfigError("Failed to start registry service", {"error": str(e)})

    async def _load_tag_registry(self) -> None:
        """Load tag registry."""
        try:
            # Load tags from configuration or database
            logger.info("Tag registry loaded")
        except Exception as e:
            raise ConfigError("Failed to load tag registry", {"error": str(e)})

    async def _load_action_registry(self) -> None:
        """Load action registry."""
        try:
            # Load actions from configuration or database
            logger.info("Action registry loaded")
        except Exception as e:
            raise ConfigError("Failed to load action registry", {"error": str(e)})

    async def _load_validation_registry(self) -> None:
        """Load validation registry."""
        try:
            # Load validations from configuration or database
            logger.info("Validation registry loaded")
        except Exception as e:
            raise ConfigError("Failed to load validation registry", {"error": str(e)})

    def _tag_exists(self, tag: str) -> bool:
        """Check if tag exists.

        Args:
            tag: Tag to check

        Returns:
            True if tag exists

        Raises:
            ValidationError: If check fails
        """
        try:
            return tag in self._tags
        except Exception as e:
            raise ValidationError("Failed to check tag existence", {"error": str(e)})

    def _action_exists(self, action: str) -> bool:
        """Check if action exists.

        Args:
            action: Action to check

        Returns:
            True if action exists

        Raises:
            ValidationError: If check fails
        """
        try:
            return action in self._actions
        except Exception as e:
            raise ValidationError("Failed to check action existence", {"error": str(e)})

    def _validation_exists(self, validation: str) -> bool:
        """Check if validation exists.

        Args:
            validation: Validation to check

        Returns:
            True if validation exists

        Raises:
            ValidationError: If check fails
        """
        try:
            return validation in self._validations
        except Exception as e:
            raise ValidationError("Failed to check validation existence", {"error": str(e)})

    def _validate_reference(self, data: Dict[str, Any], path: str, field: str, ref_type: str, exists_check, errors: List[str]) -> None:
        """Validate reference.

        Args:
            data: Data to validate
            path: Current path
            field: Field name
            ref_type: Reference type
            exists_check: Function to check existence
            errors: List to accumulate errors

        Raises:
            ValidationError: If validation fails
        """
        try:
            if field in data and not exists_check(data[field]):
                errors.append(f"{path}Unknown {ref_type} reference: {data[field]}")
        except Exception as e:
            raise ValidationError("Reference validation failed", {"path": path, "type": ref_type, "error": str(e)})

    def _validate_tag_references(self, data: Dict[str, Any], path: str, errors: List[str]) -> None:
        """Validate tag references.

        Args:
            data: Data to validate
            path: Current path
            errors: List to accumulate errors

        Raises:
            ValidationError: If validation fails
        """
        try:
            self._validate_reference(data, path, "tag", "tag", self._tag_exists, errors)
        except Exception as e:
            raise ValidationError("Tag reference validation failed", {"error": str(e)})

    def _validate_action_references(self, data: Dict[str, Any], path: str, errors: List[str]) -> None:
        """Validate action references.

        Args:
            data: Data to validate
            path: Current path
            errors: List to accumulate errors

        Raises:
            ValidationError: If validation fails
        """
        try:
            self._validate_reference(data, path, "action", "action", self._action_exists, errors)
        except Exception as e:
            raise ValidationError("Action reference validation failed", {"error": str(e)})

    def _validate_validation_references(self, data: Dict[str, Any], path: str, errors: List[str]) -> None:
        """Validate validation references.

        Args:
            data: Data to validate
            path: Current path
            errors: List to accumulate errors

        Raises:
            ValidationError: If validation fails
        """
        try:
            self._validate_reference(data, path, "validation", "validation", self._validation_exists, errors)
        except Exception as e:
            raise ValidationError("Validation reference validation failed", {"error": str(e)})

    async def validate_references(self, data: Dict[str, Any], path: str = "") -> ValidationResult:
        """Validate references in data.

        Args:
            data: Data to validate
            path: Current path

        Returns:
            Validation result

        Raises:
            ValidationError: If validation fails with an unexpected error
        """
        result = ValidationResult()

        try:
            if not isinstance(data, dict):
                return result

            try:
                # Validate references at current level
                self._validate_tag_references(data, path, result.errors)
                self._validate_action_references(data, path, result.errors)
                self._validate_validation_references(data, path, result.errors)
            except ValidationError as e:
                result.errors.append(str(e))
                result.valid = False
                return result

            # Validate nested objects
            for key, value in data.items():
                if isinstance(value, dict):
                    nested_result = await self.validate_references(value, f"{path}{key}.")
                    result.errors.extend(nested_result.errors)
                    result.warnings.extend(nested_result.warnings)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            nested_result = await self.validate_references(item, f"{path}{key}[{i}].")
                            result.errors.extend(nested_result.errors)
                            result.warnings.extend(nested_result.warnings)

            result.valid = not result.errors
            return result

        except Exception as e:
            raise ValidationError("Reference validation failed", {"error": str(e)})

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
