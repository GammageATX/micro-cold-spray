"""Configuration API router."""

from fastapi import APIRouter

from micro_cold_spray.core.config.models.config_types import (
    ConfigType, ConfigData, ConfigUpdate
)
from micro_cold_spray.core.config.service import ConfigService


router = APIRouter(prefix="/config", tags=["config"])
config_service = ConfigService()


@router.get("/{config_type}", response_model=ConfigData)
async def get_config(config_type: ConfigType) -> ConfigData:
    """Get configuration by type."""
    return await config_service.get_config(config_type)


@router.put("/{config_type}")
async def update_config(
    config_type: ConfigType,
    update: ConfigUpdate
) -> None:
    """Update configuration."""
    await config_service.update_config(config_type, update)


@router.post("/reload")
async def reload_config() -> None:
    """Reload all configurations."""
    await config_service.reload_config()


@router.get("/environment")
async def get_environment() -> str:
    """Get current environment name."""
    return config_service.get_environment()
