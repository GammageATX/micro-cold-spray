"""Configuration service endpoints."""

from typing import Dict, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from loguru import logger

from micro_cold_spray.api.config.models.config_models import (
    ConfigRequest,
    ConfigResponse,
    SchemaRequest,
    SchemaResponse,
    MessageResponse
)
from micro_cold_spray.ui.utils import get_uptime, get_memory_usage


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status (ok or error)")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    is_running: bool = Field(..., description="Whether service is running")
    uptime: float = Field(..., description="Service uptime in seconds")
    memory_usage: Dict[str, float] = Field(..., description="Memory usage stats")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    services: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Status of sub-services")


def get_config_router() -> APIRouter:
    """Create configuration router.
    
    Returns:
        APIRouter: Router with configuration endpoints
    """
    router = APIRouter(tags=["config"])

    async def get_services(request: Request):
        """Get service instances from app state."""
        return {
            "cache": request.app.state.cache,
            "file": request.app.state.file,
            "format": request.app.state.format,
            "registry": request.app.state.registry,
            "schema": request.app.state.schema
        }

    @router.get("/health", response_model=HealthResponse)
    async def health(services=Depends(get_services)):
        """Get service health status."""
        try:
            # Check all service healths
            service_health = {}
            is_healthy = True

            for name, service in services.items():
                health = await service.health()
                service_health[name] = health
                if not health.get("is_healthy", False):
                    is_healthy = False

            return HealthResponse(
                status="ok" if is_healthy else "error",
                service_name="config",
                version="1.0.0",
                is_running=is_healthy,
                uptime=get_uptime(),
                memory_usage=get_memory_usage(),
                error=None if is_healthy else "One or more services are unhealthy",
                timestamp=datetime.now(),
                services=service_health
            )
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return HealthResponse(
                status="error",
                service_name="config",
                version="1.0.0",
                is_running=False,
                uptime=0.0,
                memory_usage={},
                error=error_msg,
                timestamp=datetime.now(),
                services={}
            )

    @router.post("/config/{name}", response_model=MessageResponse)
    async def save_config(
        name: str,
        request: ConfigRequest,
        services=Depends(get_services)
    ):
        """Save configuration.
        
        Args:
            name: Configuration name
            request: Configuration request
            services: Service instances
            
        Returns:
            MessageResponse: Success response
        """
        # Validate schema if exists
        schema_name = f"{name}_schema"
        if services["schema"].get_schema(schema_name):
            services["schema"].validate_config(schema_name, request.data)

        # Format and save config
        formatted_config = services["format"].format(request.data, request.format)
        services["file"].write(f"{name}.{request.format}", formatted_config)

        # Update registry and cache
        services["registry"].register(name, request.data)
        services["cache"].set(name, request.data)

        return {"message": f"Configuration {name} saved successfully"}

    @router.get("/config/{name}", response_model=ConfigResponse)
    async def get_config(
        name: str,
        use_cache: bool = True,
        services=Depends(get_services)
    ):
        """Get configuration.
        
        Args:
            name: Configuration name
            use_cache: Whether to use cache
            services: Service instances
            
        Returns:
            ConfigResponse: Configuration data
        """
        # Try cache first
        if use_cache:
            cached = services["cache"].get(name)
            if cached:
                return {
                    "name": name,
                    "data": cached,
                    "format": "json"
                }

        # Get from registry
        data = services["registry"].get(name)
        return {
            "name": name,
            "data": data,
            "format": "json"
        }

    @router.delete("/config/{name}", response_model=MessageResponse)
    async def delete_config(name: str, services=Depends(get_services)):
        """Delete configuration.
        
        Args:
            name: Configuration name
            services: Service instances
            
        Returns:
            MessageResponse: Success response
        """
        # Delete from all services
        services["registry"].delete(name)
        services["file"].delete(f"{name}.json")
        services["cache"].delete(name)

        return {"message": f"Configuration {name} deleted successfully"}

    @router.post("/schema/{name}", response_model=MessageResponse)
    async def register_schema(
        name: str,
        request: SchemaRequest,
        services=Depends(get_services)
    ):
        """Register JSON schema.
        
        Args:
            name: Schema name
            request: Schema request
            services: Service instances
            
        Returns:
            MessageResponse: Success response
        """
        services["schema"].register_schema(name, request.schema)
        return {"message": f"Schema {name} registered successfully"}

    @router.get("/schema/{name}", response_model=SchemaResponse)
    async def get_schema(name: str, services=Depends(get_services)):
        """Get JSON schema.
        
        Args:
            name: Schema name
            services: Service instances
            
        Returns:
            SchemaResponse: Schema definition
        """
        schema = services["schema"].get_schema(name)
        return {
            "name": name,
            "schema": schema
        }

    return router
