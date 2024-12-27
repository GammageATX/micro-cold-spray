"""Data collection API router."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Request, status

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
from micro_cold_spray.api.data_collection.data_collection_models import SprayEvent


router = APIRouter(prefix="/data_collection", tags=["data_collection"])


def get_service(request: Request) -> DataCollectionService:
    """Get service instance from app state."""
    return request.app.service


@router.get("/health", response_model=ServiceHealth)
async def health(service: DataCollectionService = Depends(get_service)) -> ServiceHealth:
    """Get service health."""
    return await service.health()


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
