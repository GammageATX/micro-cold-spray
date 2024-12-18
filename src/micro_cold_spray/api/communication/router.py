"""Communication router."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from .service import CommunicationService
from ..base.errors import ErrorCode, format_error
from ..base.exceptions import ServiceError
from .endpoints import equipment_router, motion_router, tags_router
from ..config.singleton import get_config_service

# Create router with prefix (app will handle the base /api/v1 prefix)
router = APIRouter(prefix="/communication", tags=["communication"])

# Global service instance
_service: CommunicationService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global _service
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Create and start communication service
        _service = CommunicationService(config_service=config_service)
        await _service.start()
        logger.info("CommunicationService started successfully")
        
        # Store service in app state for testing
        app.state.service = _service
        
        yield
        
        # Cleanup on shutdown
        logger.info("Communication API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("Communication service stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping communication service: {e}")
            finally:
                _service = None
                app.state.service = None
            
    except ServiceError as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup
        if _service and _service.is_running:
            await _service.stop()
            _service = None
            app.state.service = None
        raise
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup
        if _service and _service.is_running:
            await _service.stop()
            _service = None
            app.state.service = None
        raise ServiceError(str(e))


# Create FastAPI app with lifespan
app = FastAPI(title="Communication API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")
app.include_router(equipment_router, prefix="/api/v1/communication")
app.include_router(motion_router, prefix="/api/v1/communication")
app.include_router(tags_router, prefix="/api/v1/communication")


def init_router(service: CommunicationService | None = None):
    """Initialize router with service instance."""
    global _service
    _service = service


def get_service() -> CommunicationService:
    """Get service instance."""
    if not _service or not _service.is_running:
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, "CommunicationService not initialized")["detail"]
        )
    return _service


@router.get("/health")
async def health_check():
    """Get service health status."""
    service = get_service()
    try:
        health_info = await service.check_health()
        
        # Add standard service info
        if "service_info" not in health_info:
            health_info["service_info"] = {}
            
        health_info["service_info"].update({
            "name": service._service_name,
            "version": service.version,
            "uptime": str(service.uptime),
            "running": service.is_running
        })
        
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
async def control_service(action: str, background_tasks: BackgroundTasks):
    """Control service operation."""
    service = get_service()
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
            
    except HTTPException:
        raise
    except ServiceError as e:
        logger.error(f"Failed to {action} service: {e}")
        error = ErrorCode.COMMUNICATION_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )
    except Exception as e:
        logger.error(f"Failed to {action} service: {e}")
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )
