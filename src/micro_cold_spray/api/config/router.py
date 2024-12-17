"""FastAPI router for configuration operations."""

from fastapi import APIRouter, HTTPException, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
import psutil
from datetime import datetime
import os
from loguru import logger

from .service import ConfigService
from ..base.exceptions import ConfigurationError
from ..base.router import add_health_endpoints
from ..base.errors import ErrorCode, format_error


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI."""
    global _service
    _service = ConfigService()  # Uses default config directory
    await _service.start()
    # Add health endpoint directly to app
    add_health_endpoints(app, _service)  # Mount to app instead of router
    yield
    if _service:
        await _service.stop()


# Create FastAPI app
app = FastAPI(title="Config API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/config", tags=["config"])
_service: Optional[ConfigService] = None


def init_router(service: ConfigService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service
    # Add health endpoints
    add_health_endpoints(router, service)


def get_service() -> ConfigService:
    """Get config service instance."""
    if _service is None:
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, "Config service not initialized")["detail"]
        )
    return _service


@router.get("/types")
async def get_config_types() -> List[Dict[str, str]]:
    """Get available configuration types."""
    return [
        {"id": "application", "name": "Application Configuration"},
        {"id": "hardware", "name": "Hardware Configuration"},
        {"id": "file_format", "name": "File Format Configuration"},
        {"id": "process", "name": "Process Configuration"},
        {"id": "state", "name": "State Configuration"},
        {"id": "tags", "name": "Tag Configuration"}
    ]


@router.get("/health")
async def health_check(
    service: ConfigService = Depends(get_service)
) -> Dict[str, Any]:
    """Check API health status."""
    try:
        # Get base service health info
        process = psutil.Process(os.getpid())
        uptime = (datetime.now() - service.start_time).total_seconds() if service.is_running else None
        memory = process.memory_info().rss

        # Get config-specific health status
        config_ok = await service.check_config_access() if service.is_running else False

        # Determine status
        if not service.is_running:
            status = "stopped"
        else:
            status = "ok" if config_ok else "error"

        return {
            "status": status,
            "uptime": uptime,
            "memory_usage": memory,
            "service_info": {
                "name": service._service_name,
                "version": getattr(service, "version", "1.0.0"),
                "running": service.is_running
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )


@router.get("/{config_type}")
async def get_config(
    config_type: str,
    service: ConfigService = Depends(get_service)
) -> Dict[str, Any]:
    """Get configuration by type."""
    try:
        config = await service.get_config(config_type)
        return {"config": config}
    except ConfigurationError as e:
        error = ErrorCode.CONFIGURATION_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e), e.context)["detail"]
        )
    except Exception as e:
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )


@router.post("/{config_type}")
async def update_config(
    config_type: str,
    config_data: Dict[str, Any],
    service: ConfigService = Depends(get_service)
) -> Dict[str, str]:
    """Update configuration."""
    try:
        from micro_cold_spray.api.config.models import ConfigUpdate
        
        backup = config_data.get("backup", True)
        should_validate = config_data.get("should_validate", True)
        data = config_data.get("data", config_data)
        
        update = ConfigUpdate(
            config_type=config_type,
            data=data,
            backup=backup,
            should_validate=should_validate
        )
        
        logger.debug(f"Creating config update: {update}")
        await service.update_config(update)
        return {"status": "updated"}
    except ConfigurationError as e:
        error = ErrorCode.CONFIGURATION_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e), e.context)["detail"]
        )
    except Exception as e:
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )


@router.post("/cache/clear")
async def clear_cache(
    service: ConfigService = Depends(get_service)
) -> Dict[str, str]:
    """Clear configuration cache."""
    try:
        await service.clear_cache()
        return {"status": "Cache cleared"}
    except Exception as e:
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )


# Include router in app
app.include_router(router)
