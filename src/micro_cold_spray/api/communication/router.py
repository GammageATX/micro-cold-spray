"""Communication router."""

from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from .service import CommunicationService
from .endpoints import equipment_router, motion_router, tags_router
from .dependencies import get_service
from ..config.singleton import get_config_service
from ..base.exceptions import ServiceError


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service_name: str
    version: str
    is_running: bool
    timestamp: datetime


class ServiceResponse(BaseModel):
    """Standard service response model."""
    status: str
    message: str
    timestamp: datetime


# Create router with prefix (app will handle the base /api/v1 prefix)
router = APIRouter(prefix="/communication", tags=["communication"])

# Global service instance
_service: Optional[CommunicationService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global _service
    try:
        # Get shared config service instance
        config_service = get_config_service()
        if not config_service.is_running:
            await config_service.start()
            if not config_service.is_running:
                raise ServiceError("ConfigService failed to start")
            logger.info("ConfigService started successfully")
        
        # Create and start communication service
        _service = CommunicationService(config_service=config_service)
        await _service.start()
        if not _service.is_running:
            raise ServiceError("CommunicationService failed to start")
        logger.info("CommunicationService started successfully")
        
        # Store service in app state for testing
        app.state.service = _service
        
        yield
        
    finally:
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


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not running"}
    }
)
async def health_check(service: CommunicationService = Depends(get_service)):
    """Check service health."""
    try:
        # Get health status
        health = await service.check_health()
        
        # Create response
        response = HealthResponse(
            status=health["status"],
            service_name=service._service_name,
            version=health["service_info"]["version"],
            is_running=health["service_info"]["running"],
            timestamp=datetime.now()
        )
        
        # Return 503 if service is not running
        if not response.is_running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service is not running"
            )
        
        return response
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/control",
    response_model=ServiceResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid control command"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def control_service(
    action: str,
    background_tasks: BackgroundTasks,
    service: CommunicationService = Depends(get_service)
):
    """Control service state."""
    valid_actions = ["start", "stop", "restart"]
    if action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {action}. Valid actions are {valid_actions}"
        )

    try:
        if action == "stop":
            await service.stop()
            message = "Communication service stopped"
        elif action == "start":
            await service.start()
            message = "Communication service started"
        else:  # restart
            await service.stop()
            await service.start()
            message = "Communication service restarted"

        background_tasks.add_task(logger.info, message)
        return ServiceResponse(
            status="ok",
            message=message,
            timestamp=datetime.now()
        )
            
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Include routers
app.include_router(router, prefix="/api/v1")
app.include_router(equipment_router, prefix="/api/v1/communication")
app.include_router(motion_router, prefix="/api/v1/communication")
app.include_router(tags_router, prefix="/api/v1/communication")
