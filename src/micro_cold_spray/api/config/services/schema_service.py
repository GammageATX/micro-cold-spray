"""Configuration schema service implementation."""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import status
from loguru import logger
from jsonschema import validate, ValidationError, SchemaError

from micro_cold_spray.utils.errors import create_error


class SchemaService:
    """Configuration schema service implementation."""

    def __init__(self):
        """Initialize service."""
        self.is_running = False
        self._start_time = None
        self._schemas: Dict[str, Dict[str, Any]] = {}

    async def start(self) -> None:
        """Start service."""
        self.is_running = True
        self._start_time = datetime.now()
        logger.info("Schema service started")

    async def stop(self) -> None:
        """Stop service."""
        self.is_running = False
        self._start_time = None
        self._schemas.clear()
        logger.info("Schema service stopped")

    def register_schema(self, name: str, schema_definition: Dict[str, Any]) -> None:
        """Register JSON schema.
        
        Args:
            name: Schema name
            schema_definition: JSON schema definition
            
        Raises:
            HTTPException: If service not running or schema invalid
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Schema service not running"
            )

        try:
            # Validate schema itself
            if not isinstance(schema_definition, dict):
                raise SchemaError("Schema must be a dictionary")
            
            # Store schema
            self._schemas[name] = schema_definition
            logger.info(f"Registered schema: {name}")
            
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid schema: {str(e)}"
            )

    def validate_config(self, name: str, config: Dict[str, Any]) -> None:
        """Validate configuration against schema.
        
        Args:
            name: Schema name
            config: Configuration to validate
            
        Raises:
            HTTPException: If service not running, schema not found, or validation fails
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Schema service not running"
            )

        schema_definition = self._schemas.get(name)
        if not schema_definition:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Schema not found: {name}"
            )

        try:
            validate(instance=config, schema=schema_definition)
        except ValidationError as e:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Configuration validation failed: {str(e)}"
            )
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Validation error: {str(e)}"
            )

    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get registered schema.
        
        Args:
            name: Schema name
            
        Returns:
            Optional[Dict[str, Any]]: Schema if found
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Schema service not running"
            )

        return self._schemas.get(name)

    def list_schemas(self) -> list[str]:
        """List registered schemas.
        
        Returns:
            list[str]: List of schema names
            
        Raises:
            HTTPException: If service not running
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Schema service not running"
            )

        return list(self._schemas.keys())

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Check schema registry
            registry_ok = self.is_running
            
            # Build component statuses
            components = {
                "registry": {
                    "status": "ok" if registry_ok else "error",
                    "error": None if registry_ok else "Schema registry not running"
                }
            }
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c["status"] == "error" for c in components.values()) else "ok"
            
            return {
                "status": overall_status,
                "service": "schema",
                "version": "1.0.0",
                "is_running": self.is_running,
                "error": None if overall_status == "ok" else "One or more components in error state",
                "components": components
            }
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "service": "schema",
                "version": "1.0.0",
                "is_running": False,
                "error": error_msg,
                "components": {
                    "registry": {"status": "error", "error": error_msg}
                }
            }
