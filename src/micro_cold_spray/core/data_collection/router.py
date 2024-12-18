"""Data collection router."""

from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, status, Depends
from pydantic import BaseModel
from loguru import logger

from micro_cold_spray.core.data_collection.services.service import DataCollectionService
from micro_cold_spray.core.config.utils import get_config_service
from micro_cold_spray.core.base import create_service_dependency
from micro_cold_spray.core.errors import DataCollectionError, ServiceError, AppErrorCode, format_error


class DataResponse(BaseModel):
    """Data response model."""
    data: Dict[str, Any]
    timestamp: datetime


class ServiceResponse(BaseModel):
    """Standard service response model."""
    status: str
    message: str
    timestamp: datetime


# Create router without prefix (app already handles the /data-collection prefix)
router = APIRouter(tags=["data-collection"])

# Global service instance
_service: Optional[DataCollectionService] = None


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
        
        # Initialize data collection service
        _service = DataCollectionService(config_service=config_service)
        await _service.start()
        if not _service.is_running:
            raise ServiceError("DataCollectionService failed to start")
        logger.info("DataCollectionService started successfully")
        
        # Store service in app state for testing
        app.state.service = _service
        
        # Mount router
        app.include_router(router)
        logger.info("Data collection router initialized")
        
        yield
        
    finally:
        # Cleanup on shutdown
        logger.info("Data Collection API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("Data collection service stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping data collection service: {e}")
            finally:
                _service = None
                app.state.service = None


# Create dependency for DataCollectionService
get_data_collection_service = create_service_dependency(DataCollectionService)


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
    service: DataCollectionService = Depends(get_data_collection_service)
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
            message = "Data collection service stopped"
        elif action == "start":
            await service.start()
            message = "Data collection service started"
        else:  # restart
            await service.stop()
            await service.start()
            message = "Data collection service restarted"

        background_tasks.add_task(logger.info, message)
        return ServiceResponse(
            status="ok",
            message=message,
            timestamp=datetime.now()
        )
            
    except DataCollectionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.DATA_COLLECTION_ERROR, str(e), e.context)
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
