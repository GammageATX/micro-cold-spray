"""Schema service for configuration validation."""

from typing import Dict, Any, List

from loguru import logger

from micro_cold_spray.api.base import BaseService
from micro_cold_spray.api.config.models import (
    ConfigSchema, ConfigValidationResult, ConfigFieldInfo
)


class SchemaService(BaseService):
    """Service for managing configuration schemas."""

    def __init__(self):
        """Initialize schema service."""
        super().__init__(service_name="schema")

    async def _start(self) -> None:
        """Start the schema service."""
        try:
            logger.info("Schema service started successfully")
        except Exception as e:
            logger.error(f"Failed to start schema service: {e}")
            raise

    async def _stop(self) -> None:
        """Stop the schema service."""
        try:
            logger.info("Schema service stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop schema service: {e}")
            raise

    def build_schema(self, schema_data: Dict[str, Any]) -> ConfigSchema:
        """Build ConfigSchema from JSON schema data.
        
        Args:
            schema_data: JSON schema data
            
        Returns:
            ConfigSchema object
        """
        try:
            # Handle string values (e.g. {"type": "string"})
            if isinstance(schema_data, str):
                return ConfigSchema(type=schema_data)

            # Extract schema properties
            schema_type = schema_data.get("type", "object")
            required_fields = schema_data.get("required", [])
            properties = schema_data.get("properties", {})
            
            # Convert properties to ConfigSchema objects
            schema_properties = {}
            for prop_name, prop_data in properties.items():
                schema_properties[prop_name] = self.build_schema(prop_data)
                # Set required flag based on whether the field is in required_fields
                schema_properties[prop_name].required = prop_name in required_fields
                
            # Handle array items
            items = None
            if "items" in schema_data:
                items = self.build_schema(schema_data["items"])

            # Handle additionalProperties
            allow_unknown = False
            if "additionalProperties" in schema_data:
                if isinstance(schema_data["additionalProperties"], bool):
                    allow_unknown = schema_data["additionalProperties"]
                else:
                    # If additionalProperties is an object, it defines the schema for additional properties
                    allow_unknown = True
                
            # Create ConfigSchema
            return ConfigSchema(
                type=schema_type,
                required=False,  # This is for the field itself, not its properties
                min_value=schema_data.get("minimum"),
                max_value=schema_data.get("maximum"),
                enum=schema_data.get("enum"),
                pattern=schema_data.get("pattern"),
                properties=schema_properties if schema_properties else None,
                items=items,
                description=schema_data.get("description"),
                format=schema_data.get("format"),
                references=schema_data.get("$ref", "").split("/") if "$ref" in schema_data else None,
                dependencies=schema_data.get("dependencies"),
                allow_unknown=allow_unknown
            )
            
        except Exception as e:
            logger.error(f"Failed to build schema: {e}")
            raise

    async def validate(self, schema: ConfigSchema, data: Any) -> ConfigValidationResult:
        """Validate data against schema.
        
        Args:
            schema: Schema to validate against
            data: Data to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        try:
            # Validate type
            if not self._validate_type(schema.type, data):
                errors.append(f"Invalid type: expected {schema.type}")
                return ConfigValidationResult(valid=False, errors=errors, warnings=warnings)
                
            # Validate object properties
            if schema.type == "object" and schema.properties:
                if not isinstance(data, dict):
                    errors.append("Expected object")
                    return ConfigValidationResult(valid=False, errors=errors, warnings=warnings)
                    
                # Check required properties
                for prop_name, prop_schema in schema.properties.items():
                    if prop_schema.required and prop_name not in data:
                        errors.append(f"Missing required property: {prop_name}")
                        continue
                        
                    if prop_name in data:
                        result = await self.validate(prop_schema, data[prop_name])
                        if not result.valid:
                            errors.extend([f"{prop_name}: {error}" for error in result.errors])
                            warnings.extend([f"{prop_name}: {warning}" for warning in result.warnings])
                            
                # Check unknown properties
                if not schema.allow_unknown:
                    unknown = set(data.keys()) - set(schema.properties.keys())
                    if unknown:
                        errors.append(f"Unknown properties: {', '.join(unknown)}")
                        
            # Validate array items
            elif schema.type == "array" and schema.items:
                if not isinstance(data, (list, tuple)):
                    errors.append("Expected array")
                    return ConfigValidationResult(valid=False, errors=errors, warnings=warnings)
                    
                for i, item in enumerate(data):
                    result = await self.validate(schema.items, item)
                    if not result.valid:
                        errors.extend([f"[{i}]: {error}" for error in result.errors])
                        warnings.extend([f"[{i}]: {warning}" for warning in result.warnings])
                        
            # Validate constraints
            constraint_errors = self._validate_constraints(schema, data)
            errors.extend(constraint_errors)
            
            return ConfigValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return ConfigValidationResult(
                valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=warnings
            )

    def _validate_type(self, expected_type: str, value: Any) -> bool:
        """Check if value matches expected type."""
        if value is None:
            return True
            
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": (list, tuple)
        }
        
        expected_types = type_map.get(expected_type)
        if expected_types:
            return isinstance(value, expected_types)
            
        # Handle special types
        if expected_type in {"state", "tag", "action"}:
            return isinstance(value, str)
            
        return True

    def _validate_constraints(self, schema: ConfigSchema, value: Any) -> List[str]:
        """Validate value against schema constraints."""
        errors = []
        
        if value is None:
            return errors
            
        # Numeric constraints
        if schema.type == "number":
            if schema.min_value is not None and value < schema.min_value:
                errors.append(f"Value must be >= {schema.min_value}")
            if schema.max_value is not None and value > schema.max_value:
                errors.append(f"Value must be <= {schema.max_value}")
                
        # String pattern
        if schema.type == "string" and schema.pattern and not isinstance(value, str):
            errors.append(f"Value must match pattern {schema.pattern}")
                
        # Enum values
        if schema.enum is not None and value not in schema.enum:
            errors.append(f"Value must be one of: {', '.join(map(str, schema.enum))}")
            
        return errors

    async def get_editable_fields(
        self, schema: ConfigSchema, data: Any, path: str = ""
    ) -> List[ConfigFieldInfo]:
        """Get list of editable fields from schema.
        
        Args:
            schema: Schema to analyze
            data: Current data values
            path: Current path in schema
            
        Returns:
            List of field information
        """
        fields = []
        
        try:
            if schema.type == "object" and schema.properties:
                for prop_name, prop_schema in schema.properties.items():
                    prop_path = f"{path}.{prop_name}" if path else prop_name
                    prop_value = data.get(prop_name) if isinstance(data, dict) else None
                    
                    # Add field info for this property
                    fields.append(ConfigFieldInfo(
                        path=prop_path,
                        type=prop_schema.type,
                        description=prop_schema.description or "",
                        constraints={
                            "required": prop_schema.required,
                            "min_value": prop_schema.min_value,
                            "max_value": prop_schema.max_value,
                            "enum": prop_schema.enum,
                            "pattern": prop_schema.pattern
                        },
                        current_value=prop_value
                    ))
                    
                    # Recursively get nested fields
                    if prop_schema.type == "object" and prop_value is not None:
                        nested_fields = await self.get_editable_fields(
                            prop_schema, prop_value, prop_path
                        )
                        fields.extend(nested_fields)
                        
            elif schema.type == "array" and schema.items and isinstance(data, (list, tuple)):
                for i, item in enumerate(data):
                    item_path = f"{path}[{i}]"
                    nested_fields = await self.get_editable_fields(
                        schema.items, item, item_path
                    )
                    fields.extend(nested_fields)
                    
            return fields
            
        except Exception as e:
            logger.error(f"Failed to get editable fields: {e}")
            return []
