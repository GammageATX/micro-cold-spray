"""Data collection API router."""

from typing import List, Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
from micro_cold_spray.api.data_collection.data_collection_models import SprayEvent
from micro_cold_spray.ui.utils import get_uptime, get_memory_usage


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status (ok or error)")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    is_running: bool = Field(..., description="Whether service is running")
    uptime: float = Field(..., description="Service uptime in seconds")
    memory_usage: Dict[str, float] = Field(..., description="Memory usage stats")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


router = APIRouter()


def get_service(request: Request) -> DataCollectionService:
    """Get service instance from app state."""
    return request.app.service


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
    }
)
async def health_check(
    service: DataCollectionService = Depends(get_service)
) -> HealthResponse:
    """Check data collection service health."""
    try:
        return HealthResponse(
            status="ok" if service.is_running else "error",
            service_name=service.name,
            version=service.version,
            is_running=service.is_running,
            uptime=get_uptime(),
            memory_usage=get_memory_usage(),
            error=None if service.is_running else "Service not running",
            timestamp=datetime.now()
        )
    except Exception as e:
        error_msg = f"Health check failed: {str(e)}"
        logger.error(error_msg)
        return HealthResponse(
            status="error",
            service_name=getattr(service, "name", "data_collection"),
            version=getattr(service, "version", "1.0.0"),
            is_running=False,
            uptime=0.0,
            memory_usage={},
            error=error_msg,
            timestamp=datetime.now()
        )


@router.post("/data/start/{sequence_id}", status_code=status.HTTP_200_OK)
async def start_collection(
    sequence_id: str,
    service: DataCollectionService = Depends(get_service)
) -> dict:
    """Start data collection for a sequence."""
    try:
        await service.start_collection(sequence_id)
        return {"message": "Data collection started"}
    except:  # noqa: E722
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to start data collection"
        )


@router.post("/data/stop", status_code=status.HTTP_200_OK)
async def stop_collection(
    service: DataCollectionService = Depends(get_service)
) -> dict:
    """Stop current data collection."""
    try:
        await service.stop_collection()
        return {"message": "Data collection stopped"}
    except:  # noqa: E722
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to stop data collection"
        )


@router.post("/data/record", status_code=status.HTTP_200_OK)
async def record_event(
    event: SprayEvent,
    service: DataCollectionService = Depends(get_service)
) -> dict:
    """Record a spray event."""
    try:
        await service.record_spray_event(event)
        return {"message": "Event recorded"}
    except:  # noqa: E722
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to record event"
        )


@router.get("/data/events/{sequence_id}", status_code=status.HTTP_200_OK)
async def get_events(
    sequence_id: str,
    service: DataCollectionService = Depends(get_service)
) -> List[SprayEvent]:
    """Get all events for a sequence."""
    try:
        return await service.get_sequence_events(sequence_id)
    except:  # noqa: E722
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to get events"
        )
