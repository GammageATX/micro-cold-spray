"""Data collection API router."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import get_uptime
from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
from micro_cold_spray.api.data_collection.data_collection_models import SprayEvent


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status (ok or error)")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    is_running: bool = Field(..., description="Whether service is running")
    uptime: float = Field(..., description="Service uptime in seconds")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


router = APIRouter(prefix="/data_collection", tags=["data_collection"])


def get_service(request: Request) -> DataCollectionService:
    """Get service instance from app state."""
    return request.app.service


@router.get("/health", response_model=HealthResponse)
async def health(service: DataCollectionService = Depends(get_service)) -> HealthResponse:
    """Get service health."""
    try:
        health_info = await service.check_health()
        return HealthResponse(
            status=health_info["status"],
            service_name=service.name,
            version=service.version,
            is_running=service.is_running,
            uptime=health_info.get("uptime", 0),
            error=health_info.get("error"),
            timestamp=datetime.now()
        )
    except Exception as e:
        return HealthResponse(
            status="error",
            service_name=service.name,
            version=service.version,
            is_running=False,
            uptime=0,
            error=str(e),
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
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to start data collection: {str(e)}"
        )


@router.post("/data/stop", status_code=status.HTTP_200_OK)
async def stop_collection(
    service: DataCollectionService = Depends(get_service)
) -> dict:
    """Stop current data collection."""
    try:
        await service.stop_collection()
        return {"message": "Data collection stopped"}
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to stop data collection: {str(e)}"
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
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to record event: {str(e)}"
        )


@router.get("/data/{sequence_id}", response_model=List[SprayEvent])
async def get_sequence_events(
    sequence_id: str,
    service: DataCollectionService = Depends(get_service)
) -> List[SprayEvent]:
    """Get all events for a sequence."""
    try:
        return await service.get_sequence_events(sequence_id)
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to get sequence events: {str(e)}"
        )
