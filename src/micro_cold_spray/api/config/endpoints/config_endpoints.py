"""Configuration service endpoints."""

from typing import Dict, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from loguru import logger

from micro_cold_spray.api.config.models.config_models import (
    ConfigRequest,
    ConfigResponse,
    SchemaRequest,
    SchemaResponse,
    MessageResponse
)
from micro_cold_spray.utils.errors import create_error


def get_config_router() -> APIRouter:
    """Get configuration router.
    
    Returns:
        APIRouter: Router instance
    """
    router = APIRouter(prefix="/config", tags=["config"])
    
    @router.get("/{name}", response_model=ConfigResponse)
    async def get_config(name: str, request: Request) -> ConfigResponse:
        """Get configuration by name."""
        try:
            # Read from file
            raw_data = request.app.state.file.read(f"{name}.yaml")
            
            # Parse YAML content
            config_data = request.app.state.format.parse(raw_data, "yaml")
            
            return ConfigResponse(
                name=name,
                data=config_data,
                format="yaml"
            )
            
        except Exception as e:
            logger.error(f"Failed to get config {name}: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to get config {name}: {str(e)}"
            )
    
    @router.put("/{name}", response_model=MessageResponse)
    async def update_config(name: str, config: ConfigRequest, request: Request) -> MessageResponse:
        """Update configuration."""
        try:
            # Validate against schema if exists
            schema = request.app.state.schema.get_schema(name)
            if schema:
                request.app.state.schema.validate_config(name, config.data)
            
            # Format data
            formatted_data = request.app.state.format.format(config.data, config.format)
            
            # Write to file
            request.app.state.file.write(f"{name}.yaml", formatted_data)
            
            return MessageResponse(message=f"Configuration {name} updated successfully")
            
        except Exception as e:
            logger.error(f"Failed to update config {name}: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to update config {name}: {str(e)}"
            )
    
    @router.post("/validate/{name}", response_model=MessageResponse)
    async def validate_config(name: str, config: ConfigRequest, request: Request) -> MessageResponse:
        """Validate configuration against schema."""
        try:
            # Get schema
            schema = request.app.state.schema.get_schema(name)
            if not schema:
                return MessageResponse(message=f"No schema found for {name}, skipping validation")
            
            # Validate config
            request.app.state.schema.validate_config(name, config.data)
            
            return MessageResponse(message=f"Configuration {name} is valid")
            
        except Exception as e:
            logger.error(f"Validation failed for {name}: {e}")
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Validation failed: {str(e)}"
            )
    
    @router.get("/schema/{name}", response_model=SchemaResponse)
    async def get_schema(name: str, request: Request) -> SchemaResponse:
        """Get schema by name."""
        try:
            schema = request.app.state.schema.get_schema(name)
            if not schema:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Schema not found: {name}"
                )
            
            return SchemaResponse(
                name=name,
                schema_definition=schema
            )
            
        except Exception as e:
            logger.error(f"Failed to get schema {name}: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to get schema {name}: {str(e)}"
            )
    
    @router.put("/schema/{name}", response_model=MessageResponse)
    async def update_schema(name: str, schema: SchemaRequest, request: Request) -> MessageResponse:
        """Update schema."""
        try:
            # Register schema
            request.app.state.schema.register_schema(name, schema.schema_definition)
            
            return MessageResponse(message=f"Schema {name} updated successfully")
            
        except Exception as e:
            logger.error(f"Failed to update schema {name}: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to update schema {name}: {str(e)}"
            )
    
    return router
