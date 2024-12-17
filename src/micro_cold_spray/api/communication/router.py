"""Communication router."""

from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Depends
from loguru import logger

from .service import CommunicationService
from ..base.router import add_health_endpoints
from ..base.errors import ErrorCode, format_error
from ..base.exceptions import ServiceError
from ..config.singleton import get_config_service

# Create router without prefix (app already handles the /communication prefix)
router = APIRouter(tags=["communication"])

_service: Optional[CommunicationService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global _service
    
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Initialize communication service
        _service = CommunicationService(config_service=config_service)
        await _service.start()
        logger.info("CommunicationService started successfully")
        
        # Add health endpoints
        add_health_endpoints(app, _service)
        # Mount router to app with prefix
        app.include_router(router, prefix="/communication")
        logger.info("Communication router initialized")
        
        yield  # Application runs here
        
        # Cleanup on shutdown
        logger.info("Communication API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("Communication service stopped successfully")
                _service = None
            except Exception as e:
                logger.error(f"Error stopping communication service: {e}")
                
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup of any partially initialized services
        if _service and _service.is_running:
            await _service.stop()
        raise


def get_communication_service() -> CommunicationService:
    """Get communication service instance."""
    if _service is None:
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, "Communication service not initialized")["detail"]
        )
    return _service


def init_router(service: CommunicationService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service
    # Add health endpoints
    add_health_endpoints(router, service)


@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    service: CommunicationService = Depends(get_communication_service)
) -> Dict[str, Any]:
    """Check service health."""
    try:
        health_info = await service.check_health()
        return health_info
    except ServiceError as e:
        logger.error(f"Health check failed: {e}")
        error = ErrorCode.HEALTH_CHECK_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )


@router.post("/control")
async def control_service(
    action: str,
    background_tasks: BackgroundTasks,
    service: CommunicationService = Depends(get_communication_service)
) -> Dict[str, str]:
    """Control service operation."""
    try:
        valid_actions = ["start", "stop", "restart"]
        if action not in valid_actions:
            error = ErrorCode.INVALID_ACTION
            raise HTTPException(
                status_code=error.get_status_code(),
                detail=format_error(
                    error,
                    f"Invalid action: {action}",
                    {"valid_actions": valid_actions}
                )["detail"]
            )

        if action == "stop":
            await service.stop()
            background_tasks.add_task(logger.info, "Communication service stopped")
            return {"status": "stopped"}
        elif action == "start":
            await service.start()
            background_tasks.add_task(logger.info, "Communication service started")
            return {"status": "started"}
        elif action == "restart":
            await service.stop()
            await service.start()
            background_tasks.add_task(logger.info, "Communication service restarted")
            return {"status": "restarted"}
    except ServiceError as e:
        logger.error(f"Failed to {action} service: {e}")
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Failed to {action} service: {e}")
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )


# Add startup and shutdown events for testing
async def startup():
    """Initialize services on startup."""
    global _service
    
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Initialize communication service
        _service = CommunicationService(config_service=config_service)
        await _service.start()
        logger.info("CommunicationService started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        if _service and _service.is_running:
            await _service.stop()
        raise


async def shutdown():
    """Handle shutdown tasks."""
    global _service
    if _service:
        try:
            await _service.stop()
            _service = None
        except Exception as e:
            logger.error(f"Error stopping communication service: {e}")

# Add startup and shutdown events to router for testing
router.startup = startup
router.shutdown = shutdown
