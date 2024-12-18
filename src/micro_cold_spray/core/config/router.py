"""FastAPI router for configuration management endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, Response, status

from .service import (
    ConfigData,
    ConfigMetadata,
    get_config_service,
)

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("/", response_model=List[ConfigMetadata])
async def list_configs() -> List[ConfigMetadata]:
    """List all available configurations."""
    service = get_config_service()
    return service.list_configs()


@router.get("/{name}", response_model=ConfigData)
async def get_config(name: str) -> ConfigData:
    """Get a configuration by name."""
    service = get_config_service()
    config = service.get_config(name)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{name}' not found"
        )
    return config


@router.put("/{name}", response_model=ConfigData)
async def save_config(name: str, config: ConfigData) -> ConfigData:
    """Save a configuration."""
    service = get_config_service()
    
    # Validate configuration
    if not service.validate_config(config):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid configuration data"
        )
    
    service.save_config(name, config)
    return config


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(name: str) -> Response:
    """Delete a configuration."""
    service = get_config_service()
    if not service.delete_config(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{name}' not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
