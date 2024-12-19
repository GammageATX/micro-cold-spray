"""Registry service for config references."""

from typing import Dict, Any, Set, Callable
from loguru import logger

from micro_cold_spray.api.base import BaseService
from micro_cold_spray.api.base.base_exceptions import ConfigurationError, ValidationError
from micro_cold_spray.api.config.models.config_models import ConfigValidationResult


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
            logger.error(f"Failed to start registry service: {e}")
            raise ConfigurationError(
                "Failed to start registry service",
                {"error": str(e)}
            )

    async def validate_references(
        self,
        data: Dict[str, Any]
    ) -> ConfigValidationResult:
        """Validate references in config data."""
        errors = []
        warnings = []

        try:
            self._validate_tag_references(data, "", errors)
            self._validate_action_references(data, "", errors)
            self._validate_validation_references(data, "", errors)
        except ValidationError as e:
            errors.append(str(e))
        except Exception as e:
            logger.error(f"Unexpected error during reference validation: {e}")
            raise ValidationError(
                "Reference validation failed",
                {"error": str(e)}
            )

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
        """Validate tag references recursively."""
        try:
            self._validate_reference(
                data, path, "tag", "tag", self._tag_exists, errors
            )
        except Exception as e:
            raise ValidationError(
                "Tag reference validation failed",
                {
                    "path": path,
                    "error": str(e)
                }
            )

    def _validate_action_references(
        self,
        data: Any,
        path: str,
        errors: list
    ) -> None:
        """Validate action references recursively."""
        try:
            self._validate_reference(
                data, path, "action", "action", self._action_exists, errors
            )
        except Exception as e:
            raise ValidationError(
                "Action reference validation failed",
                {
                    "path": path,
                    "error": str(e)
                }
            )

    def _validate_validation_references(
        self,
        data: Any,
        path: str,
        errors: list
    ) -> None:
        """Validate validation references recursively."""
        try:
            self._validate_reference(
                data, path, "validation", "validation", self._validation_exists, errors
            )
        except Exception as e:
            raise ValidationError(
                "Validation reference validation failed",
                {
                    "path": path,
                    "error": str(e)
                }
            )

    def _validate_reference(
        self,
        data: Any,
        path: str,
        ref_type: str,
        ref_key: str,
        exists_check: Callable[[str], bool],
        errors: list
    ) -> None:
        """Generic reference validation."""
        try:
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == ref_key and isinstance(value, str):
                        if not exists_check(value):
                            raise ValidationError(
                                f"Unknown {ref_type} reference",
                                {
                                    "reference": value,
                                    "path": f"{path}.{key}",
                                    "type": ref_type
                                }
                            )
                    else:
                        self._validate_reference(
                            value, f"{path}.{key}",
                            ref_type, ref_key, exists_check, errors
                        )
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    self._validate_reference(
                        item, f"{path}[{i}]",
                        ref_type, ref_key, exists_check, errors
                    )
        except ValidationError as e:
            errors.append(str(e))
        except Exception as e:
            logger.error(f"Unexpected error in reference validation: {e}")
            raise ValidationError(
                "Reference validation failed",
                {
                    "path": path,
                    "type": ref_type,
                    "error": str(e)
                }
            )

    def _tag_exists(self, tag: str) -> bool:
        """Check if tag exists in registry."""
        try:
            return tag in self._tags
        except Exception as e:
            logger.error(f"Error checking tag existence: {e}")
            raise ValidationError(
                "Failed to check tag existence",
                {"tag": tag, "error": str(e)}
            )

    def _action_exists(self, action: str) -> bool:
        """Check if action exists in registry."""
        try:
            return action in self._actions
        except Exception as e:
            logger.error(f"Error checking action existence: {e}")
            raise ValidationError(
                "Failed to check action existence",
                {"action": action, "error": str(e)}
            )

    def _validation_exists(self, validation: str) -> bool:
        """Check if validation exists in registry."""
        try:
            return validation in self._validations
        except Exception as e:
            logger.error(f"Error checking validation existence: {e}")
            raise ValidationError(
                "Failed to check validation existence",
                {"validation": validation, "error": str(e)}
            )

    async def _load_tag_registry(self) -> None:
        """Load tag registry."""
        try:
            # TODO: Load from config or service
            # For now, allow any tag format
            self._tags = set()
            logger.info("Tag registry loaded")
        except Exception as e:
            logger.error(f"Failed to load tag registry: {e}")
            raise ConfigurationError(
                "Failed to load tag registry",
                {"error": str(e)}
            )

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
            logger.error(f"Failed to load action registry: {e}")
            raise ConfigurationError(
                "Failed to load action registry",
                {"error": str(e)}
            )

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
            logger.error(f"Failed to load validation registry: {e}")
            raise ConfigurationError(
                "Failed to load validation registry",
                {"error": str(e)}
            )

    async def validate_tag(self, tag: str) -> bool:
        """Validate a tag exists in the registry.
        
        Args:
            tag: Tag to validate
            
        Returns:
            True if tag is valid, False otherwise
        """
        try:
            return tag in self._tag_registry
        except Exception as e:
            logger.error(f"Failed to validate tag {tag}: {e}")
            return False

    async def update_tag_references(
        self, config_data: Dict[str, Any], old_tag: str, new_tag: str
    ) -> bool:
        """Update tag references in config data.
        
        Args:
            config_data: Configuration data to update
            old_tag: Old tag to replace
            new_tag: New tag to use
            
        Returns:
            True if any references were updated, False otherwise
        """
        try:
            updated = False
            
            def update_dict(d: Dict[str, Any]) -> None:
                nonlocal updated
                for key, value in d.items():
                    if isinstance(value, str) and value == old_tag:
                        d[key] = new_tag
                        updated = True
                    elif isinstance(value, dict):
                        update_dict(value)
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, str) and item == old_tag:
                                value[i] = new_tag
                                updated = True
                            elif isinstance(item, dict):
                                update_dict(item)
            
            update_dict(config_data)
            return updated
            
        except Exception as e:
            logger.error(f"Failed to update tag references from {old_tag} to {new_tag}: {e}")
            return False
