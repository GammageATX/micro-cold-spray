"""Data collection API router."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Request, status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
from micro_cold_spray.api.data_collection.data_collection_models import SprayEvent


router = APIRouter(
    prefix="/data",
    tags=["data"]
)


def get_service(request: Request) -> DataCollectionService:
    """Get service instance from app state."""
    return request.app.service


@router.get("/health", status_code=status.HTTP_200_OK)
async def check_health(
    service: DataCollectionService = Depends(get_service)
) -> dict:
    """Check data collection service health."""
    try:
        return await service.check_health()
    except:  # noqa: E722
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Health check failed"
        )


@router.post("/start/{sequence_id}", status_code=status.HTTP_200_OK)
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


@router.post("/stop", status_code=status.HTTP_200_OK)
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


@router.post("/record", status_code=status.HTTP_200_OK)
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


@router.get("/events/{sequence_id}", status_code=status.HTTP_200_OK)
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
