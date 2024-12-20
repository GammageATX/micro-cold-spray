"""Configuration registry service implementation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, Set, Any

from loguru import logger
from fastapi import status, HTTPException

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import (
    create_error,
    AppErrorCode,
    service_error,
    validation_error,
    config_error
)
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
            HTTPException: If service fails to start (503)
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
            raise service_error(
                message="Failed to start registry service",
                context={"error": str(e)}
            )

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
            raise service_error(
                message="Failed to start registry service",
                context={"error": str(e)}
            )

    async def _load_tag_registry(self) -> None:
        """Load tag registry."""
        try:
            # Load tags from configuration or database
            logger.info("Tag registry loaded")
        except Exception as e:
            raise create_error(
                message="Failed to load tag registry",
                error_code=AppErrorCode.CONFIG_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                context={"error": str(e)}
            )

    async def _load_action_registry(self) -> None:
        """Load action registry."""
        try:
            # Load actions from configuration or database
            logger.info("Action registry loaded")
        except Exception as e:
            raise create_error(
                message="Failed to load action registry",
                error_code=AppErrorCode.CONFIG_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                context={"error": str(e)}
            )

    async def _load_validation_registry(self) -> None:
        """Load validation registry."""
        try:
            # Load validations from configuration or database
            logger.info("Validation registry loaded")
        except Exception as e:
            raise create_error(
                message="Failed to load validation registry",
                error_code=AppErrorCode.CONFIG_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                context={"error": str(e)}
            )

    def _tag_exists(self, tag: str) -> bool:
        """Check if tag exists.

        Args:
            tag: Tag to check

        Returns:
            True if tag exists

        Raises:
            HTTPException: If check fails (422)
        """
        try:
            return tag in self._tags
        except Exception as e:
            raise validation_error(
                message="Failed to check tag existence",
                context={"tag": tag, "error": str(e)}
            )

    def _action_exists(self, action: str) -> bool:
        """Check if action exists.

        Args:
            action: Action to check

        Returns:
            True if action exists

        Raises:
            HTTPException: If check fails (422)
        """
        try:
            return action in self._actions
        except Exception as e:
            raise validation_error(
                message="Failed to check action existence",
                context={"action": action, "error": str(e)}
            )

    def _validation_exists(self, validation: str) -> bool:
        """Check if validation exists.

        Args:
            validation: Validation to check

        Returns:
            True if validation exists

        Raises:
            HTTPException: If check fails (422)
        """
        try:
            return validation in self._validations
        except Exception as e:
            raise validation_error(
                message="Failed to check validation existence",
                context={"validation": validation, "error": str(e)}
            )

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
            HTTPException: If validation fails (422)
        """
        try:
            if field in data and not exists_check(data[field]):
                errors.append(f"{path}Unknown {ref_type} reference: {data[field]}")
        except Exception as e:
            raise validation_error(
                message="Reference validation failed",
                context={
                    "path": path,
                    "type": ref_type,
                    "field": field,
                    "error": str(e)
                }
            )

    def _validate_tag_references(self, data: Dict[str, Any], path: str, errors: List[str]) -> None:
        """Validate tag references.

        Args:
            data: Data to validate
            path: Current path
            errors: List to accumulate errors

        Raises:
            HTTPException: If validation fails (422)
        """
        try:
            self._validate_reference(data, path, "tag", "tag", self._tag_exists, errors)
        except Exception as e:
            raise validation_error(
                message="Tag reference validation failed",
                context={"error": str(e)}
            )

    def _validate_action_references(self, data: Dict[str, Any], path: str, errors: List[str]) -> None:
        """Validate action references.

        Args:
            data: Data to validate
            path: Current path
            errors: List to accumulate errors

        Raises:
            HTTPException: If validation fails (422)
        """
        try:
            self._validate_reference(data, path, "action", "action", self._action_exists, errors)
        except Exception as e:
            raise validation_error(
                message="Action reference validation failed",
                context={"error": str(e)}
            )

    def _validate_validation_references(self, data: Dict[str, Any], path: str, errors: List[str]) -> None:
        """Validate validation references.

        Args:
            data: Data to validate
            path: Current path
            errors: List to accumulate errors

        Raises:
            HTTPException: If validation fails (422)
        """
        try:
            self._validate_reference(data, path, "validation", "validation", self._validation_exists, errors)
        except Exception as e:
            raise validation_error(
                message="Validation reference validation failed",
                context={"error": str(e)}
            )

    async def validate_references(self, data: Dict[str, Any], path: str = "") -> ValidationResult:
        """Validate references in data.

        Args:
            data: Data to validate
            path: Current path

        Returns:
            Validation result

        Raises:
            HTTPException: If validation fails with an unexpected error (422)
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
            except HTTPException as e:
                result.errors.append(str(e))
                result.valid = False
                return result

            # Validate nested objects
            for key, value in data.items():
                if isinstance(value, dict):
                    nested_result = await self.validate_references(value, f"{path}{key}.")
                    result.errors.extend(nested_result.errors)
                    result.warnings.extend(nested_result.warnings)

            result.valid = len(result.errors) == 0
            return result

        except Exception as e:
            raise validation_error(
                message="Reference validation failed",
                context={"error": str(e)}
            )

    def register_config_type(self, config_type: Type[ConfigData]) -> None:
        """Register configuration type.

        Args:
            config_type: Configuration type to register

        Raises:
            HTTPException: If type already exists (409)
        """
        if config_type.__name__ in self._config_types:
            raise create_error(
                message=f"Config type {config_type.__name__} already exists",
                error_code=AppErrorCode.CONFIG_ERROR,
                status_code=status.HTTP_409_CONFLICT,
                context={"type": config_type.__name__}
            )

        self._config_types[config_type.__name__] = config_type
        logger.info("Registered config type: {}", config_type.__name__)

    def get_config_type(self, type_name: str) -> Type[ConfigData]:
        """Get configuration type.

        Args:
            type_name: Configuration type name

        Returns:
            Configuration type

        Raises:
            HTTPException: If type not found (404)
        """
        if type_name not in self._config_types:
            raise create_error(
                message=f"Config type {type_name} not found",
                error_code=AppErrorCode.CONFIG_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
                context={"type": type_name}
            )

        return self._config_types[type_name]

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
            raise config_error("Config type not specified")

        if config.metadata.config_type not in self._config_types:
            raise config_error(f"Config type {config.metadata.config_type} not registered")

        try:
            self._configs[config.metadata.config_type] = config
            logger.info("Registered config: {}", config.metadata.config_type)
        except Exception as e:
            raise config_error("Failed to register config", {"error": str(e)})

    async def get_config(self, config_type: str) -> ConfigData:
        """Get configuration.

        Args:
            config_type: Configuration type

        Returns:
            Configuration data

        Raises:
            HTTPException: If config not found (404)
        """
        if config_type not in self._configs:
            raise create_error(
                message=f"Config {config_type} not found",
                error_code=AppErrorCode.CONFIG_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
                context={"type": config_type}
            )

        return self._configs[config_type]

    async def update_config(self, config: ConfigData) -> None:
        """Update configuration.

        Args:
            config: Configuration data

        Raises:
            HTTPException: If update fails (400)
        """
        try:
            self._configs[config.metadata.config_type] = config
            logger.info("Updated config: {}", config.metadata.config_type)
        except Exception as e:
            raise config_error(
                message="Failed to update config",
                context={"error": str(e)}
            )

    async def delete_config(self, config_type: str) -> None:
        """Delete configuration.

        Args:
            config_type: Configuration type

        Raises:
            HTTPException: If config not found (404) or delete fails (500)
        """
        if config_type not in self._configs:
            raise create_error(
                message=f"Config {config_type} not found",
                error_code=AppErrorCode.CONFIG_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
                context={"type": config_type}
            )

        try:
            del self._configs[config_type]
            logger.info("Deleted config: {}", config_type)
        except Exception as e:
            raise create_error(
                message="Failed to delete config",
                error_code=AppErrorCode.CONFIG_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                context={"error": str(e)}
            )

    async def check_health(self) -> dict:
        """Check service health.

        Returns:
            Health check result
        """
        health = await super().check_health()
        health["service_info"].update({
            "config_types": len(self._config_types),
            "configs": len(self._configs),
            "tags": len(self._tags),
            "actions": len(self._actions),
            "validations": len(self._validations)
        })
        return health
