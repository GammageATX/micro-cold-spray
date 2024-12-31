"""Schema service for process API."""

from typing import Dict, Any, List
from pathlib import Path
import yaml
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error


class SchemaService:
    """Service for managing process schemas."""

    def __init__(self):
        """Initialize schema service."""
        self._service_name = "schema"
        self._schemas: Dict[str, Dict] = {}
        self._schema_dir = Path("schemas/process")
        
    async def initialize(self) -> None:
        """Initialize service and load schemas."""
        try:
            # Create schema directory if it doesn't exist
            self._schema_dir.mkdir(parents=True, exist_ok=True)
            
            # Load all schema files
            schema_files = self._schema_dir.glob("*.yaml")
            for schema_file in schema_files:
                schema_name = schema_file.stem
                with open(schema_file, "r") as f:
                    self._schemas[schema_name] = yaml.safe_load(f)
                    
            logger.info(f"Loaded {len(self._schemas)} schemas")
            
        except Exception as e:
            error_msg = f"Failed to initialize schema service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def list_schemas(self) -> List[str]:
        """List available schemas."""
        return list(self._schemas.keys())

    async def get_schema(self, name: str) -> Dict[str, Any]:
        """Get schema by name."""
        if name not in self._schemas:
            error_msg = f"Schema '{name}' not found"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=error_msg
            )
        return self._schemas[name]
    
    async def validate(self, name: str, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate data against schema."""
        try:
            if name not in self._schemas:
                error_msg = f"Schema '{name}' not found"
                logger.error(error_msg)
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=error_msg
                )
            
            schema = self._schemas[name]
            errors = []
            
            # Basic structure validation
            if schema["root_key"] not in data:
                errors.append(f"Missing root key '{schema['root_key']}'")
                return False, errors
                
            # Required fields
            content = data[schema["root_key"]]
            for field in schema["required_fields"]:
                if field not in content:
                    errors.append(f"Missing required field '{field}'")
                    
            # Field types
            for field, field_type in schema["field_types"].items():
                if field in content:
                    if field_type == "number":
                        if not isinstance(content[field], (int, float)):
                            errors.append(f"Field '{field}' must be a number")
                    elif field_type == "integer":
                        if not isinstance(content[field], int):
                            errors.append(f"Field '{field}' must be an integer")
                    elif field_type == "string":
                        if not isinstance(content[field], str):
                            errors.append(f"Field '{field}' must be a string")
                            
            # Field ranges
            for field, range_info in schema.get("field_ranges", {}).items():
                if field in content:
                    value = content[field]
                    if "min" in range_info and value < range_info["min"]:
                        errors.append(f"Field '{field}' must be >= {range_info['min']}")
                    if "max" in range_info and value > range_info["max"]:
                        errors.append(f"Field '{field}' must be <= {range_info['max']}")
                        
            return len(errors) == 0, errors
            
        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )
