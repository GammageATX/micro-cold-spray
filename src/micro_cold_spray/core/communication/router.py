"""Communication router."""

from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, status, Depends
from pydantic import BaseModel
from loguru import logger

from micro_cold_spray.core.communication.services.service import CommunicationService
from micro_cold_spray.core.communication.endpoints import equipment_router, motion_router, tags_router
from micro_cold_spray.core.config.utils import get_config_service
from micro_cold_spray.core.base import create_service_dependency
from micro_cold_spray.core.errors import ServiceError, CommunicationError, AppErrorCode, format_error


class ServiceResponse(BaseModel):
    """Standard service response model."""
    status: str
    message: str
    timestamp: datetime


# Create router without prefix (app already handles the /communication prefix)
router = APIRouter(tags=["communication"])

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
        
        # Mount routers
        app.include_router(router)
        app.include_router(equipment_router)
        app.include_router(motion_router)
        app.include_router(tags_router)
        logger.info("Communication routers initialized")
        
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


# Create dependency for CommunicationService
get_communication_service = create_service_dependency(CommunicationService)


@router.post(
    "/control",
    response_model=ServiceResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid action"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def control_service(
    action: str,
    background_tasks: BackgroundTasks,
    service: CommunicationService = Depends(get_communication_service)
):
    """Control service operation."""
    valid_actions = ["start", "stop", "restart"]
    if action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_error(AppErrorCode.INVALID_ACTION, f"Invalid action: {action}. Valid actions are {valid_actions}")
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
            
    except CommunicationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.COMMUNICATION_ERROR, str(e), e.context)
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
