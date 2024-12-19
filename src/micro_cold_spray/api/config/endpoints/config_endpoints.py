"""Configuration service endpoints."""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from loguru import logger

from micro_cold_spray.api.base.base_errors import ConfigError
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.models import (
    ConfigData,
    ConfigUpdate,
    ConfigValidationResult,
    ConfigFieldInfo,
    TagRemapRequest
)
from micro_cold_spray.api.config.utils.config_singleton import get_config_service

# Create router
router = APIRouter(tags=["config"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check service health."""
    try:
        service = get_config_service()
        return await service.check_health()
    except ConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


def init_router(app_instance=None):
    """Initialize router with app instance.
    
    Args:
        app_instance: Optional FastAPI app instance
    """
    if app_instance:
        app_instance.include_router(router)


@router.get("/config/types")
async def get_config_types() -> List[Dict[str, str]]:
    """Get available configuration types."""
    try:
        service = get_config_service()
        return await service.get_config_types()
    except ConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get config types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/config/{config_type}")
async def get_config(config_type: str) -> ConfigData:
    """Get configuration data.
    
    Args:
        config_type: Type of configuration to get
        
    Returns:
        ConfigData: Configuration data
    """
    try:
        service = get_config_service()
        return await service.get_config(config_type)
    except ConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get config {config_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/config/{config_type}")
async def update_config(
    config_type: str,
    update: ConfigUpdate
) -> ConfigValidationResult:
    """Update configuration data.
    
    Args:
        config_type: Type of configuration to update
        update: Configuration update request
        
    Returns:
        ConfigValidationResult: Validation result
    """
    try:
        service = get_config_service()
        return await service.update_config(update)
    except ConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update config {config_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/config/cache/clear")
async def clear_cache():
    """Clear the configuration cache."""
    try:
        service = get_config_service()
        await service.clear_cache()
        return {"status": "Cache cleared"}
    except ConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
