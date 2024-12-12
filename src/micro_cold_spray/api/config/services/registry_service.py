"""Registry service for config references."""

from typing import Dict, Any, Set
from loguru import logger

from ...base import BaseService
from ..models import ConfigValidationResult
from ..exceptions import ConfigurationError


class RegistryService(BaseService):
    """Service for managing config references and registries."""

    def __init__(self):
        """Initialize registry service."""
        super().__init__(service_name="registry")
        self._tags: Set[str] = set()
        self._actions: Set[str] = set()
        self._validations: Set[str] = set()

    async def _start(self) -> None:
        """Initialize registry service."""
        try:
            # Load registries
            await self._load_tag_registry()
            await self._load_action_registry()
            await self._load_validation_registry()
            logger.info("Registry service started")
        except Exception as e:
            raise ConfigurationError(f"Failed to start registry service: {e}")

    async def validate_references(
        self,
        data: Dict[str, Any]
    ) -> ConfigValidationResult:
        """Validate references in config data.
        
        Args:
            data: Config data to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []

        try:
            self._validate_tag_references(data, "", errors)
            self._validate_action_references(data, "", errors)
            self._validate_validation_references(data, "", errors)
        except Exception as e:
            errors.append(f"Reference validation failed: {str(e)}")

        return ConfigValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_tag_references(
        self,
        data: Any,
        path: str,
        errors: list
    ) -> None:
        """Validate tag references recursively.
        
        Args:
            data: Data to validate
            path: Current path for error messages
            errors: List to collect errors
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "tag" and isinstance(value, str):
                    if not self._tag_exists(value):
                        errors.append(f"{path}.{key}: Unknown tag {value}")
                else:
                    self._validate_tag_references(value, f"{path}.{key}", errors)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_tag_references(item, f"{path}[{i}]", errors)

    def _validate_action_references(
        self,
        data: Any,
        path: str,
        errors: list
    ) -> None:
        """Validate action references recursively.
        
        Args:
            data: Data to validate
            path: Current path for error messages
            errors: List to collect errors
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "action" and isinstance(value, str):
                    if not self._action_exists(value):
                        errors.append(f"{path}.{key}: Unknown action {value}")
                else:
                    self._validate_action_references(value, f"{path}.{key}", errors)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_action_references(item, f"{path}[{i}]", errors)

    def _validate_validation_references(
        self,
        data: Any,
        path: str,
        errors: list
    ) -> None:
        """Validate validation references recursively.
        
        Args:
            data: Data to validate
            path: Current path for error messages
            errors: List to collect errors
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "validation" and isinstance(value, str):
                    if not self._validation_exists(value):
                        errors.append(f"{path}.{key}: Unknown validation {value}")
                else:
                    self._validate_validation_references(value, f"{path}.{key}", errors)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_validation_references(item, f"{path}[{i}]", errors)

    def _tag_exists(self, tag: str) -> bool:
        """Check if tag exists in registry."""
        return tag in self._tags

    def _action_exists(self, action: str) -> bool:
        """Check if action exists in registry."""
        return action in self._actions

    def _validation_exists(self, validation: str) -> bool:
        """Check if validation exists in registry."""
        return validation in self._validations

    async def _load_tag_registry(self) -> None:
        """Load tag registry."""
        try:
            # TODO: Load from config or service
            # For now, allow any tag format
            self._tags = set()
            logger.info("Tag registry loaded")
        except Exception as e:
            raise ConfigurationError(f"Failed to load tag registry: {e}")

    async def _load_action_registry(self) -> None:
        """Load action registry."""
        try:
            # TODO: Load from config or service
            # For now, use basic set of actions
            self._actions = {
                "read",
                "write",
                "monitor"
            }
            logger.info("Action registry loaded")
        except Exception as e:
            raise ConfigurationError(f"Failed to load action registry: {e}")

    async def _load_validation_registry(self) -> None:
        """Load validation registry."""
        try:
            # TODO: Load from config or service
            # For now, use basic set of validations
            self._validations = {
                "range",
                "enum",
                "pattern"
            }
            logger.info("Validation registry loaded")
        except Exception as e:
            raise ConfigurationError(f"Failed to load validation registry: {e}")
