"""Configuration API endpoints."""

from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, status, Depends
from pydantic import BaseModel
from loguru import logger

from micro_cold_spray.api.base import BaseRouter
from micro_cold_spray.api.base.base_exceptions import ConfigError, ServiceError
from micro_cold_spray.api.base.base_errors import AppErrorCode, format_error
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.utils import get_config_service


class ConfigResponse(BaseModel):
    """Configuration response model."""
    config: Dict[str, Any]
    timestamp: datetime


class ServiceResponse(BaseModel):
    """Standard service response model."""
    status: str
    message: str
    timestamp: datetime


# Create router with prefix
router = BaseRouter(
    service_class=ConfigService,
    prefix="/config",
    tags=["config"]
)


def get_service() -> ConfigService:
    """Get service instance."""
    service = get_config_service()
    if not service or not service.is_running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, "ConfigService not initialized")
        )
    return service


@router.get(
    "/",
    response_model=ConfigResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def get_config(service: ConfigService = Depends(get_service)):
    """Get current configuration."""
    try:
        config = await service.get_config()
        return ConfigResponse(
            config=config,
            timestamp=datetime.now()
        )
    except ConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.CONFIGURATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


@router.post(
    "/reload",
    response_model=ServiceResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def reload_config(
    background_tasks: BackgroundTasks,
    service: ConfigService = Depends(get_service)
):
    """Reload configuration from disk."""
    try:
        await service.reload_config()
        message = "Configuration reloaded successfully"
        background_tasks.add_task(logger.info, message)
        return ServiceResponse(
            status="ok",
            message=message,
            timestamp=datetime.now()
        )
    except ConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.CONFIGURATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )
