"""Configuration schema service implementation."""

import json
from typing import Dict, Any, Optional
from fastapi import status
from loguru import logger
from jsonschema import validate, ValidationError, SchemaError

from micro_cold_spray.api.base import create_error
from micro_cold_spray.api.config.services.base_config_service import BaseConfigService


class SchemaService(BaseConfigService):
    """Configuration schema service implementation."""

    def __init__(self):
        """Initialize service."""
        super().__init__(name="schema")
        self._schemas: Dict[str, Dict[str, Any]] = {}

    async def _start(self) -> None:
        """Start implementation."""
        logger.info("Schema service started")

    async def _stop(self) -> None:
        """Stop implementation."""
        self._schemas.clear()
        logger.info("Schema service stopped")

    def register_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """Register JSON schema.
        
        Args:
            name: Schema name
            schema: JSON schema definition
            
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
            if not isinstance(schema, dict):
                raise SchemaError("Schema must be a dictionary")
            
            # Store schema
            self._schemas[name] = schema
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

        schema = self._schemas.get(name)
        if not schema:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Schema not found: {name}"
            )

        try:
            validate(instance=config, schema=schema)
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

    async def health(self) -> dict:
        """Get service health status."""
        health = await super().health()
        health.update({
            "schema_count": len(self._schemas),
            "schemas": list(self._schemas.keys())
        })
        return health
