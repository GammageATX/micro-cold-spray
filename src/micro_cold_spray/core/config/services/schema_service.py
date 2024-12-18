"""Schema service for config operations."""

from pathlib import Path
import json
import re
from typing import Dict, Any, List, Optional
from fastapi import status, HTTPException
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from micro_cold_spray.core.base import BaseService
from micro_cold_spray.core.config.models import (
    ConfigSchema, ConfigFieldInfo)


class SchemaService(BaseService):
    """Service for schema operations."""

    def __init__(self, schema_dir: Path):
        """Initialize schema service."""
        super().__init__(service_name="schema")
        self._schema_dir = schema_dir
        self._schemas: Dict[str, ConfigSchema] = {}

    async def _start(self) -> None:
        """Start schema service."""
        try:
            self._schema_dir.mkdir(parents=True, exist_ok=True)
            await self._load_schemas()
            logger.info(f"Schema service started with {len(self._schemas)} schemas")
        except Exception as e:
            logger.error(f"Failed to start schema service: {e}")
            self._error = str(e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to start schema service: {str(e)}"
            )

    async def _check_health(self) -> Dict[str, Any]:
        """Check schema service health."""
        return {
            "schemas": len(self._schemas),
            "schema_types": list(self._schemas.keys())
        }

    async def _load_schemas(self) -> None:
        """Load all schema files."""
        try:
            for schema_file in self._schema_dir.glob("*.json"):
                schema_type = schema_file.stem
                with open(schema_file, "r") as f:
                    schema_data = json.load(f)
                    self._schemas[schema_type] = self.build_schema(schema_data)
        except Exception as e:
            logger.error(f"Failed to load schemas: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load schemas: {str(e)}"
            )

    def get_schema(self, schema_type: str) -> Optional[ConfigSchema]:
        """Get schema by type."""
        if not schema_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schema type cannot be empty"
            )
        return self._schemas.get(schema_type)

    def build_schema(self, schema_data: Dict[str, Any]) -> ConfigSchema:
        """Build schema from raw data."""
        try:
            if not isinstance(schema_data, dict):
                raise ValueError("Schema must be an object")
            return ConfigSchema(**schema_data)
        except PydanticValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Schema validation failed",
                    "errors": e.errors()
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid schema format: {str(e)}"
            )

    async def validate_config(self, schema_type: str, config_data: Dict[str, Any]) -> List[str]:
        """Validate configuration against schema."""
        schema = self.get_schema(schema_type)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema not found: {schema_type}"
            )
        
        try:
            errors = []
            self._validate_against_schema(config_data, schema, "", errors)
            return errors
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Validation failed: {str(e)}"
            )

    def _validate_against_schema(
        self,
        data: Any,
        schema: ConfigSchema,
        path: str,
        errors: List[str]
    ) -> None:
        """Validate data against schema recursively."""
        validators = {
            "object": self._validate_object,
            "array": self._validate_array,
            "string": self._validate_string,
            "number": self._validate_number,
            "boolean": self._validate_boolean
        }
        
        validator = validators.get(schema.type)
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
        
        # Check required fields
        if schema.required:
            for field in schema.required:
                if field not in data:
                    errors.append(f"{path}: Missing required field '{field}'")
        
        # Validate properties
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
        
        if schema.minimum is not None and data < schema.minimum:
            errors.append(f"{path}: Value must be >= {schema.minimum}")
            
        if schema.maximum is not None and data > schema.maximum:
            errors.append(f"{path}: Value must be <= {schema.maximum}")

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

    async def get_editable_fields(
        self,
        schema: ConfigSchema,
        data: Dict[str, Any],
        path: str = ""
    ) -> List[ConfigFieldInfo]:
        """Get list of editable fields from schema."""
        fields: List[ConfigFieldInfo] = []
        
        if not schema or not schema.properties:
            return fields
            
        for field_name, field_schema in schema.properties.items():
            field_path = f"{path}.{field_name}" if path else field_name
            current_value = data.get(field_name) if data else None
            
            if field_schema.type == "object" and field_schema.properties:
                # Recursively get fields for nested objects
                nested_data = current_value if isinstance(current_value, dict) else {}
                fields.extend(
                    await self.get_editable_fields(
                        field_schema, nested_data, field_path
                    )
                )
            else:
                # Add leaf field
                fields.append(
                    ConfigFieldInfo(
                        path=field_path,
                        type=field_schema.type,
                        description=field_schema.description or "",
                        required=field_name in (schema.required or []),
                        current_value=current_value,
                        enum_values=field_schema.enum,
                        pattern=field_schema.pattern,
                        minimum=field_schema.minimum,
                        maximum=field_schema.maximum
                    )
                )
                
        return fields
