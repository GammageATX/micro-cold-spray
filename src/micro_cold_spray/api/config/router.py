from fastapi import APIRouter, HTTPException
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


@router.get("/{config_type}")
async def get_config(config_type: str) -> Dict[str, Any]:
    """Get configuration by type."""
    service = get_service()
    try:
        config = await service.get_config(config_type)
        return {"config": config}
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{config_type}")
async def update_config(
    config_type: str,
    config_data: Dict[str, Any]
) -> Dict[str, str]:
    """Update configuration."""
    service = get_service()
    try:
        await service.update_config(config_type, config_data)
        return {"status": "updated"}
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/validate/{config_type}")
async def validate_config(
    config_type: str,
    config_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate configuration data."""
    service = get_service()
    try:
        await service.validate_config(config_type, config_data)
        return {"valid": True}
    except ConfigurationError as e:
        raise HTTPException(
            status_code=400,
            detail={"valid": False, "error": str(e)}
        )


@router.post("/tags/mapping")
async def update_tag_mapping(
    tag_path: str,
    plc_tag: str
) -> Dict[str, str]:
    """Update PLC tag mapping."""
    service = get_service()
    try:
        await service.update_tag_mapping(tag_path, plc_tag)
        return {"status": "updated"}
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e)) 