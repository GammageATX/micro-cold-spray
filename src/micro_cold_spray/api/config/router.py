"""FastAPI router for configuration operations."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional

from .service import ConfigService, ConfigurationError

router = APIRouter(prefix="/config", tags=["config"])
_service: Optional[ConfigService] = None


def init_router(service: ConfigService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service


def get_service() -> ConfigService:
    """Get config service instance."""
    if _service is None:
        raise RuntimeError("Config service not initialized")
    return _service


@router.get("/health")
async def health_check(
    service: ConfigService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Check API health status.
    
    Returns:
        Dict containing health status and any error details
    """
    try:
        config_ok = await service.check_config_access()
        if not config_ok:
            return {
                "status": "error",
                "message": "Cannot access config files"
            }
            
        return {
            "status": "ok",
            "message": "Service healthy"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/{config_type}")
async def get_config(
    config_type: str,
    service: ConfigService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Get configuration by type.
    
    Args:
        config_type: Type of configuration to retrieve
        
    Returns:
        Dict containing configuration data
    """
    try:
        config = await service.get_config(config_type)
        return {"config": config}
    except ConfigurationError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/{config_type}")
async def update_config(
    config_type: str,
    config_data: Dict[str, Any],
    service: ConfigService = Depends(get_service)
) -> Dict[str, str]:
    """
    Update configuration.
    
    Args:
        config_type: Type of configuration to update
        config_data: New configuration data
        
    Returns:
        Dict containing operation status
    """
    try:
        await service.update_config(config_type, config_data)
        return {"status": "updated"}
    except ConfigurationError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/{config_type}/validate")
async def validate_config(
    config_type: str,
    config_data: Dict[str, Any],
    service: ConfigService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Validate configuration data.
    
    Args:
        config_type: Type of configuration to validate
        config_data: Configuration data to validate
        
    Returns:
        Dict containing validation result
    """
    try:
        await service.validate_config(config_type, config_data)
        return {
            "valid": True,
            "message": "Configuration is valid"
        }
    except ConfigurationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "valid": False,
                "error": str(e),
                "context": e.context
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/tags/mapping")
async def update_tag_mapping(
    tag_path: str,
    plc_tag: str,
    service: ConfigService = Depends(get_service)
) -> Dict[str, str]:
    """Update PLC tag mapping."""
    try:
        await service.update_tag_mapping(tag_path, plc_tag)
        return {"status": "updated"}
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))
