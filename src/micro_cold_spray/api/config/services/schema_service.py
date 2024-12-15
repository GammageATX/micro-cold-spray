"""Schema service for configuration validation."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import re

from loguru import logger

from micro_cold_spray.api.base import BaseService
from micro_cold_spray.api.base.exceptions import ConfigurationError
from micro_cold_spray.api.config.models import ConfigSchema


class SchemaService(BaseService):
    """Service for schema validation."""

    def __init__(self, schema_dir: Path):
        """Initialize schema service."""
        super().__init__(service_name="schema")
        self._schema_dir = schema_dir
        self._schema_dir.mkdir(parents=True, exist_ok=True)
        self._schemas: Dict[str, ConfigSchema] = {}

    async def _start(self) -> None:
        """Start schema service."""
        try:
            self._schema_dir.mkdir(exist_ok=True)
            await self._load_schemas()
            logger.info("Schema service started with {} schemas", len(self._schemas))
        except Exception as e:
            raise ConfigurationError("Failed to start schema service", {"error": str(e)})

    async def _load_schemas(self) -> None:
        """Load all schema files."""
        try:
            for schema_file in self._schema_dir.glob("*.json"):
                schema_type = schema_file.stem
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)
                    
                if not isinstance(schema_data, dict):
                    raise ConfigurationError(
                        "Invalid schema format",
                        {"schema": schema_type}
                    )
                    
                self._schemas[schema_type] = ConfigSchema(**schema_data)
                logger.debug("Loaded schema: {}", schema_type)
                
        except Exception as e:
            raise ConfigurationError("Failed to load schemas", {"error": str(e)})

    def get_schema(self, schema_type: str) -> Optional[ConfigSchema]:
        """Get schema by type."""
        return self._schemas.get(schema_type)

    def build_schema(self, schema_data: Dict[str, Any]) -> ConfigSchema:
        """Build a schema from raw data."""
        return ConfigSchema(**schema_data)

    def validate_config(
            self,
            config_type: str,
            config_data: Dict[str, Any]
    ) -> List[str]:
        """Validate configuration against schema."""
        schema = self.get_schema(config_type)
        if not schema:
            raise ConfigurationError(
                "Schema not found",
                {
                    "config_type": config_type,
                    "available_schemas": list(self._schemas.keys())
                }
            )
            
        try:
            errors = []
            self._validate_against_schema(config_data, schema, "", errors)
            return errors
        except Exception as e:
            logger.error("Unexpected validation error: {}", e)
            raise ConfigurationError(
                "Validation failed",
                {
                    "config_type": config_type,
                    "error": str(e)
                }
            )

    def _validate_against_schema(
            self,
            data: Any,
            schema: ConfigSchema,
            path: str,
            errors: List[str]
    ) -> None:
        """Validate data against schema recursively."""
        validation_methods = {
            "object": self._validate_object,
            "array": self._validate_array,
            "string": self._validate_string,
            "number": self._validate_number,
            "boolean": self._validate_boolean,
            "tag": self._validate_reference,
            "action": self._validate_reference,
            "state": self._validate_reference,
            "sequence": self._validate_reference
        }

        validator = validation_methods.get(schema.type)
        if validator:
            validator(data, schema, path, errors)
        else:
            errors.append(f"{path}: Unknown schema type '{schema.type}'")

    def _validate_object(
            self,
            data: Any,
            schema: ConfigSchema,
            path: str,
            errors: List[str]
    ) -> None:
        """Validate object type data."""
        if not isinstance(data, dict):
            errors.append(f"{path}: Expected object, got {type(data).__name__}")
            return

        self._validate_required_fields(data, schema, path, errors)
        self._validate_object_properties(data, schema, path, errors)

    def _validate_required_fields(
            self,
            data: Dict[str, Any],
            schema: ConfigSchema,
            path: str,
            errors: List[str]
    ) -> None:
        """Validate required fields in object."""
        if schema.required:
            for field in schema.required:
                if field not in data:
                    errors.append(f"{path}: Missing required field '{field}'")

    def _validate_object_properties(
            self,
            data: Dict[str, Any],
            schema: ConfigSchema,
            path: str,
            errors: List[str]
    ) -> None:
        """Validate object properties."""
        if schema.properties:
            for key, value in data.items():
                if key in schema.properties:
                    field_path = f"{path}.{key}" if path else key
                    self._validate_against_schema(
                        value,
                        schema.properties[key],
                        field_path,
                        errors
                    )
                elif not schema.allow_unknown:
                    errors.append(f"{path}: Unknown field '{key}'")

    def _validate_array(
            self,
            data: Any,
            schema: ConfigSchema,
            path: str,
            errors: List[str]
    ) -> None:
        """Validate array type data."""
        if not isinstance(data, list):
            errors.append(f"{path}: Expected array, got {type(data).__name__}")
            return

        if schema.items:
            for i, item in enumerate(data):
                item_path = f"{path}[{i}]"
                self._validate_against_schema(item, schema.items, item_path, errors)

    def _validate_string(
            self,
            data: Any,
            schema: ConfigSchema,
            path: str,
            errors: List[str]
    ) -> None:
        """Validate string type data."""
        if not isinstance(data, str):
            errors.append(f"{path}: Expected string, got {type(data).__name__}")
            return

        if schema.pattern and not re.match(schema.pattern, data):
            errors.append(f"{path}: String does not match pattern '{schema.pattern}'")

        if schema.enum and data not in schema.enum:
            errors.append(f"{path}: Value must be one of {schema.enum}")

    def _validate_number(
            self,
            data: Any,
            schema: ConfigSchema,
            path: str,
            errors: List[str]
    ) -> None:
        """Validate number type data."""
        if not isinstance(data, (int, float)):
            errors.append(f"{path}: Expected number, got {type(data).__name__}")
            return

        if schema.min_value is not None and data < schema.min_value:
            errors.append(f"{path}: Value must be >= {schema.min_value}")

        if schema.max_value is not None and data > schema.max_value:
            errors.append(f"{path}: Value must be <= {schema.max_value}")

    def _validate_boolean(
            self,
            data: Any,
            schema: ConfigSchema,
            path: str,
            errors: List[str]
    ) -> None:
        """Validate boolean type data."""
        if not isinstance(data, bool):
            errors.append(f"{path}: Expected boolean, got {type(data).__name__}")

    def _validate_reference(
            self,
            data: Any,
            schema: ConfigSchema,
            path: str,
            errors: List[str]
    ) -> None:
        """Validate reference type data (tag, action, state, sequence)."""
        if not isinstance(data, str):
            errors.append(f"{path}: Expected string reference, got {type(data).__name__}")
            return

        if schema.references and data not in schema.references:
            errors.append(f"{path}: Invalid reference '{data}'")

        if schema.dependencies:
            for dep in schema.dependencies:
                if dep not in data:
                    errors.append(f"{path}: Missing dependency '{dep}'")
