"""Data collection API router."""

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, Request, status

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
from micro_cold_spray.api.data_collection.data_collection_models import (
    SprayEvent,
    CollectionResponse,
    SprayEventResponse,
    SprayEventListResponse
)


router = APIRouter(prefix="/data_collection", tags=["data_collection"])


def get_service(request: Request) -> DataCollectionService:
    """Get service instance from app state."""
    return request.app.service


@router.get("/health", response_model=ServiceHealth)
async def health(service: DataCollectionService = Depends(get_service)) -> ServiceHealth:
    """Get service health status.
    
    Returns:
        ServiceHealth: Health status
    """
    return await service.health()


@router.post("/data/start/{sequence_id}", response_model=CollectionResponse)
async def start_collection(
    sequence_id: str,
    service: DataCollectionService = Depends(get_service)
) -> CollectionResponse:
    """Start data collection for a sequence.
    
    Args:
        sequence_id: Sequence identifier
        service: Data collection service
        
    Returns:
        CollectionResponse: Operation response
        
    Raises:
        HTTPException: If operation fails
    """
    try:
        await service.start_collection(sequence_id)
        return CollectionResponse(message="Data collection started")
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to start data collection: {str(e)}"
        )


@router.post("/data/stop", response_model=CollectionResponse)
async def stop_collection(
    service: DataCollectionService = Depends(get_service)
) -> CollectionResponse:
    """Stop current data collection.
    
    Args:
        service: Data collection service
        
    Returns:
        CollectionResponse: Operation response
        
    Raises:
        HTTPException: If operation fails
    """
    try:
        await service.stop_collection()
        return CollectionResponse(message="Data collection stopped")
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to stop data collection: {str(e)}"
        )


@router.post("/data/record", response_model=SprayEventResponse)
async def record_event(
    event: SprayEvent,
    service: DataCollectionService = Depends(get_service)
) -> SprayEventResponse:
    """Record a spray event.
    
    Args:
        event: Spray event to record
        service: Data collection service
        
    Returns:
        SprayEventResponse: Operation response with recorded event
        
    Raises:
        HTTPException: If operation fails
    """
    try:
        await service.record_spray_event(event)
        return SprayEventResponse(
            message="Event recorded successfully",
            event=event
        )
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to record event: {str(e)}"
        )


@router.get("/data/{sequence_id}", response_model=SprayEventListResponse)
async def get_sequence_events(
    sequence_id: str,
    service: DataCollectionService = Depends(get_service)
) -> SprayEventListResponse:
    """Get all events for a sequence.
    
    Args:
        sequence_id: Sequence identifier
        service: Data collection service
        
    Returns:
        SprayEventListResponse: List of spray events
        
    Raises:
        HTTPException: If operation fails
    """
    try:
        events = await service.get_sequence_events(sequence_id)
        return SprayEventListResponse(
            message=f"Retrieved {len(events)} events",
            events=events
        )
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to get sequence events: {str(e)}"
        )
