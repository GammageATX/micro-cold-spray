"""Schema validation service for configuration management."""

from typing import Any, Dict, List, Optional, Type

from fastapi import status
from loguru import logger
from pydantic import BaseModel, ValidationError

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.config.models.config_models import ConfigData


class SchemaService(BaseService):
    """Schema validation service for configuration management."""

    def __init__(self):
        """Initialize schema service."""
        super().__init__()
        self._schemas: Dict[str, Type[BaseModel]] = {}

    async def _start(self) -> None:
        """Start schema service."""
        try:
            self._schemas.clear()
            self._is_running = True
            logger.info("Schema service started")
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to start schema service",
                context={"error": str(e)},
                cause=e
            )

    async def _stop(self) -> None:
        """Stop schema service."""
        try:
            self._schemas.clear()
            self._is_running = False
            logger.info("Schema service stopped")
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to stop schema service",
                context={"error": str(e)},
                cause=e
            )

    async def register_schema(self, schema_type: Type[BaseModel]) -> None:
        """Register schema type.
        
        Args:
            schema_type: Schema type to register
            
        Raises:
            HTTPException: If service not running (503) or schema already exists (409)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Schema service is not running"
            )

        if schema_type.__name__ in self._schemas:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message=f"Schema {schema_type.__name__} already exists",
                context={"schema": schema_type.__name__}
            )

        self._schemas[schema_type.__name__] = schema_type
        logger.info(f"Registered schema: {schema_type.__name__}")

    async def validate_schema(self, schema_name: str, data: Dict[str, Any]) -> None:
        """Validate data against schema.
        
        Args:
            schema_name: Schema name
            data: Data to validate
            
        Raises:
            HTTPException: If service not running (503), schema not found (404), or validation fails (422)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Schema service is not running"
            )

        if schema_name not in self._schemas:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Schema {schema_name} not found",
                context={"schema": schema_name}
            )

        try:
            self._schemas[schema_name](**data)
        except ValidationError as e:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Schema validation failed",
                context={"schema": schema_name, "errors": e.errors()},
                cause=e
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check service health.
        
        Returns:
            Dict[str, Any]: Health check response
        """
        return {
            "status": "running" if self.is_running else "stopped",
            "is_healthy": self.is_running,
            "context": {
                "service": "schema",
                "schemas": len(self._schemas)
            }
        }
