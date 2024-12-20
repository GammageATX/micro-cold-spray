"""Configuration service endpoints."""

from fastapi import APIRouter, Depends, Request
from loguru import logger

from micro_cold_spray.api.config.models.config_models import (
    ConfigRequest,
    ConfigResponse,
    SchemaRequest,
    SchemaResponse,
    HealthResponse,
    MessageResponse
)


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
        service_health = {}
        is_healthy = True

        for name, service in services.items():
            health = await service.health()
            service_health[name] = health
            if not health.get("is_healthy", False):
                is_healthy = False

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "is_healthy": is_healthy,
            "services": service_health
        }

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
