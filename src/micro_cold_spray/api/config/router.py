"""FastAPI router for configuration operations."""

from fastapi import APIRouter, HTTPException, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List
import psutil
from datetime import datetime
import os
from loguru import logger

from .service import ConfigService, ConfigurationError
from ..base.router import add_health_endpoints

# Create FastAPI app
app = FastAPI(title="Config API")

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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global _service
    _service = ConfigService()  # Uses default config directory
    await _service.start()
    # Add health endpoint directly to app
    add_health_endpoints(app, _service)  # Mount to app instead of router


def init_router(service: ConfigService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service
    # Add health endpoints
    add_health_endpoints(router, service)


def get_service() -> ConfigService:
    """Get config service instance."""
    if _service is None:
        raise RuntimeError("Config service not initialized")
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
        uptime = (datetime.now() - service.start_time).total_seconds()
        memory = process.memory_info().rss

        # Get config-specific health status
        config_ok = await service.check_config_access()

        return {
            "status": "ok" if service.is_running and config_ok else "error",
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
        return {
            "status": "error",
            "error": str(e),
            "service_info": {
                "name": service._service_name,
                "running": False
            }
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


@router.post("/cache/clear")
async def clear_cache(
    service: ConfigService = Depends(get_service)
) -> Dict[str, str]:
    """Clear configuration cache."""
    try:
        await service.clear_cache()
        return {"status": "Cache cleared"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)}
        )


# Include router in app
app.include_router(router)
