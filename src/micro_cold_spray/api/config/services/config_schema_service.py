"""Configuration schema service implementation."""

import json
from pathlib import Path
from typing import Dict, Optional, Any, List, Union
import re
from datetime import datetime

from loguru import logger
from fastapi import status, HTTPException

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import (
    create_error,
    AppErrorCode,
    service_error,
    config_error,
    validation_error
)
from micro_cold_spray.api.config.models.config_models import ConfigSchema


class ConfigSchemaService(BaseService):
    """Configuration schema service implementation."""

    def __init__(self, service_name: str, schema_dir: Path) -> None:
        """Initialize service.

        Args:
            service_name: Service name
            schema_dir: Schema directory
        """
        super().__init__(service_name)
        self._schema_dir = schema_dir
        self._schemas: Dict[str, ConfigSchema] = {}

    async def start(self) -> None:
        """Start service.

        Raises:
            HTTPException: If schema loading fails (503)
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
                message="Failed to start schema service",
                context={"error": str(e)}
            )

    async def _start(self) -> None:
        """Start schema service."""
        self._schema_dir.mkdir(parents=True, exist_ok=True)
        await self._load_schemas()
        logger.info("Schema service started with {} schemas", len(self._schemas))

    async def _stop(self) -> None:
        """Stop schema service."""
        self._schemas.clear()

    async def _load_schemas(self) -> None:
        """Load all schema files."""
        has_errors = False
        error_details = []
        for schema_file in self._schema_dir.glob("*.json"):
            try:
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)

                if not isinstance(schema_data, dict):
                    logger.warning("Invalid schema format in {}", schema_file)
                    error_details.append(f"Invalid format in {schema_file.name}")
                    has_errors = True
                    continue

                self._schemas[schema_file.stem] = ConfigSchema(**schema_data)
                logger.debug("Loaded schema: {}", schema_file.stem)
            except Exception as e:
                logger.warning("Failed to load schema {}: {}", schema_file, e)
                error_details.append(f"Failed to load {schema_file.name}: {str(e)}")
                has_errors = True
                continue

        if has_errors:
            raise create_error(
                message="Failed to load one or more schemas",
                error_code=AppErrorCode.CONFIG_ERROR,
                status_code=status.HTTP_400_BAD_REQUEST,
                context={"errors": error_details}
            )

    def get_schema(self, schema_type: str) -> Optional[ConfigSchema]:
        """Get schema by type.

        Args:
            schema_type: Schema type

        Returns:
            Schema if found, None otherwise
        """
        return self._schemas.get(schema_type)

    def build_schema(self, schema_data: Union[Dict[str, Any], ConfigSchema]) -> ConfigSchema:
        """Build schema from raw data.

        Args:
            schema_data: Raw schema data or existing ConfigSchema

        Returns:
            Built schema

        Raises:
            HTTPException: If schema is invalid (400)
        """
        try:
            if isinstance(schema_data, ConfigSchema):
                return schema_data
            return ConfigSchema(**schema_data)
        except Exception as e:
            raise config_error(
                message=f"Invalid schema format: {str(e)}",
                context={"error": str(e)}
            )

    def validate_config(self, schema_type: str, config: Dict[str, Any]) -> List[str]:
        """Validate configuration against schema.

        Args:
            schema_type: Schema type
            config: Configuration to validate

        Returns:
            List of validation errors, empty if valid

        Raises:
            HTTPException: If schema not found (404) or validation fails (422)
        """
        schema = self.get_schema(schema_type)
        if not schema:
            raise create_error(
                message=f"Schema {schema_type} not found",
                error_code=AppErrorCode.CONFIG_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
                context={"schema_type": schema_type}
            )

        try:
            errors = self._validate_against_schema(config, schema)
            if errors:
                raise validation_error(
                    message="Configuration validation failed",
                    context={"errors": errors}
                )
            return errors
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise validation_error(
                message="Validation failed",
                context={"error": str(e)}
            )

    def _validate_type(self, data: Any, expected_type: str, path: str) -> Optional[str]:
        """Validate type of data.

        Args:
            data: Value to validate
            expected_type: Expected type
            path: Current path in schema

        Returns:
            Error message if validation fails, None otherwise
        """
        if expected_type not in {"object", "array", "string", "number", "boolean", "tag", "action", "state", "sequence"}:
            return f"{path}Unknown schema type: {expected_type}"

        type_checks = {
            "object": lambda x: isinstance(x, dict),
            "array": lambda x: isinstance(x, list),
            "string": lambda x: isinstance(x, str),
            "number": lambda x: isinstance(x, (int, float)),
            "boolean": lambda x: isinstance(x, bool)
        }

        if expected_type in type_checks and not type_checks[expected_type](data):
            return f"{path}Expected {expected_type}, got {type(data).__name__}"
        return None

    def _validate_object(self, data: Dict[str, Any], schema: ConfigSchema, path: str, errors: List[str]) -> None:
        """Validate object against schema.

        Args:
            data: Object to validate
            schema: Schema to validate against
            path: Current path in schema
            errors: List to accumulate errors
        """
        if schema.required:
            for field in schema.required:
                if field not in data:
                    errors.append(f"{path}Missing required field: {field}")
                elif data[field] is None:
                    errors.append(f"{path}Field cannot be null: {field}")

        for prop_name, prop_value in data.items():
            if prop_name in (schema.properties or {}):
                prop_schema = schema.properties[prop_name]
                if isinstance(prop_schema, dict):
                    prop_schema = self.build_schema(prop_schema)
                self._validate_against_schema(prop_value, prop_schema, f"{path}{prop_name}.", errors)

    def _validate_array(self, data: List[Any], schema: ConfigSchema, path: str, errors: List[str]) -> None:
        """Validate array against schema.

        Args:
            data: Array to validate
            schema: Schema to validate against
            path: Current path in schema
            errors: List to accumulate errors
        """
        if schema.items:
            item_schema = schema.items
            if isinstance(item_schema, dict):
                item_schema = self.build_schema(item_schema)
            for i, item in enumerate(data):
                self._validate_against_schema(item, item_schema, f"{path}[{i}].", errors)

    def _validate_string(self, data: str, schema: ConfigSchema, path: str, errors: List[str]) -> None:
        """Validate string against schema.

        Args:
            data: String to validate
            schema: Schema to validate against
            path: Current path in schema
            errors: List to accumulate errors
        """
        if schema.pattern and not re.match(schema.pattern, data):
            errors.append(f"{path}String does not match pattern: {schema.pattern}")
        if schema.min_value and len(data) < schema.min_value:
            errors.append(f"{path}String length {len(data)} is less than minimum {schema.min_value}")
        if schema.max_value and len(data) > schema.max_value:
            errors.append(f"{path}String length {len(data)} is greater than maximum {schema.max_value}")
        if schema.enum and data not in schema.enum:
            errors.append(f"{path}Value must be one of {schema.enum}")

    def _validate_number(self, data: Union[int, float], schema: ConfigSchema, path: str, errors: List[str]) -> None:
        """Validate number against schema.

        Args:
            data: Number to validate
            schema: Schema to validate against
            path: Current path in schema
            errors: List to accumulate errors
        """
        if schema.min_value is not None and data < schema.min_value:
            errors.append(f"{path}Value must be >= {schema.min_value}")
        if schema.max_value is not None and data > schema.max_value:
            errors.append(f"{path}Value must be <= {schema.max_value}")

    def _validate_reference(self, data: str, schema: ConfigSchema, path: str, errors: List[str]) -> None:
        """Validate reference against schema.

        Args:
            data: Reference to validate
            schema: Schema to validate against
            path: Current path in schema
            errors: List to accumulate errors
        """
        if schema.references and data not in schema.references:
            errors.append(f"{path}Invalid reference: {data}. Must be one of {schema.references}")

        if schema.dependencies:
            for dep in schema.dependencies:
                if dep not in data:
                    errors.append(f"{path}Missing dependency: {dep}")

    def _validate_against_schema(self, data: Any, schema: ConfigSchema, path: str = "", errors: List[str] = None) -> List[str]:
        """Validate value against schema.

        Args:
            data: Value to validate
            schema: Schema to validate against
            path: Current path in the schema (for nested validation)
            errors: List to accumulate errors

        Returns:
            List of validation errors, empty if valid
        """
        if errors is None:
            errors = []

        # Type validation
        type_error = self._validate_type(data, schema.type, path)
        if type_error:
            errors.append(type_error)
            return errors

        # Value validation
        if schema.type == "object":
            self._validate_object(data, schema, path, errors)
        elif schema.type == "array":
            self._validate_array(data, schema, path, errors)
        elif schema.type == "string":
            self._validate_string(data, schema, path, errors)
        elif schema.type == "number":
            self._validate_number(data, schema, path, errors)
        elif schema.type in {"tag", "action", "state", "sequence"}:
            self._validate_reference(data, schema, path, errors)

        return errors

    async def add_schema(self, schema_type: str, schema: ConfigSchema) -> None:
        """Add schema.

        Args:
            schema_type: Schema type
            schema: Schema to add

        Raises:
            HTTPException: If schema already exists (409) or save fails (500)
        """
        if schema_type in self._schemas:
            raise create_error(
                message=f"Schema {schema_type} already exists",
                error_code=AppErrorCode.CONFIG_ERROR,
                status_code=status.HTTP_409_CONFLICT,
                context={"schema_type": schema_type}
            )

        try:
            schema_file = self._schema_dir / f"{schema_type}.json"
            with open(schema_file, 'w') as f:
                json.dump(schema.model_dump(), f, indent=2)

            self._schemas[schema_type] = schema
            logger.info("Added schema: {}", schema_type)
        except Exception as e:
            raise create_error(
                message=f"Failed to add schema: {str(e)}",
                error_code=AppErrorCode.CONFIG_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                context={"error": str(e)}
            )

    async def update_schema(self, schema_type: str, schema: ConfigSchema) -> None:
        """Update schema.

        Args:
            schema_type: Schema type
            schema: Updated schema

        Raises:
            HTTPException: If schema not found (404) or save fails (500)
        """
        if schema_type not in self._schemas:
            raise create_error(
                message=f"Schema {schema_type} not found",
                error_code=AppErrorCode.CONFIG_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
                context={"schema_type": schema_type}
            )

        try:
            schema_file = self._schema_dir / f"{schema_type}.json"
            with open(schema_file, 'w') as f:
                json.dump(schema.model_dump(), f, indent=2)

            self._schemas[schema_type] = schema
            logger.info("Updated schema: {}", schema_type)
        except Exception as e:
            raise create_error(
                message=f"Failed to update schema: {str(e)}",
                error_code=AppErrorCode.CONFIG_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                context={"error": str(e)}
            )

    async def delete_schema(self, schema_type: str) -> None:
        """Delete schema.

        Args:
            schema_type: Schema type to delete

        Raises:
            HTTPException: If schema not found (404) or delete fails (500)
        """
        if schema_type not in self._schemas:
            raise create_error(
                message=f"Schema {schema_type} not found",
                error_code=AppErrorCode.CONFIG_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
                context={"schema_type": schema_type}
            )

        try:
            schema_file = self._schema_dir / f"{schema_type}.json"
            schema_file.unlink()
            del self._schemas[schema_type]
            logger.info("Deleted schema: {}", schema_type)
        except Exception as e:
            raise create_error(
                message=f"Failed to delete schema: {str(e)}",
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
            "schema_dir": str(self._schema_dir),
            "schema_count": len(self._schemas),
            "schemas": list(self._schemas.keys())
        })
        return health
