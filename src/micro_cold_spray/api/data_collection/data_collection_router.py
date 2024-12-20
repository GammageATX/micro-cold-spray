"""Data collection API router."""

from typing import List
from fastapi import APIRouter, Depends, status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_router import get_service
from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
from micro_cold_spray.api.data_collection.data_collection_models import SprayEvent


router = APIRouter(
    prefix="/data",
    tags=["data"]
)


@router.get("/health", status_code=status.HTTP_200_OK)
async def check_health(
    service: DataCollectionService = Depends(get_service(DataCollectionService))
) -> dict:
    """Check data collection service health.
    
    Returns:
        Health status information
        
    Raises:
        HTTPException: If health check fails
    """
    try:
        return await service.check_health()
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Health check failed",
            context={"error": str(e)},
            cause=e
        )


@router.post("/start/{sequence_id}", status_code=status.HTTP_200_OK)
async def start_collection(
    sequence_id: str,
    service: DataCollectionService = Depends(get_service(DataCollectionService))
) -> dict:
    """Start data collection for a sequence.
    
    Args:
        sequence_id: ID of sequence to collect data for
        
    Returns:
        Success response
        
    Raises:
        HTTPException: If collection cannot be started
    """
    try:
        await service.start_collection(sequence_id)
        return {"message": "Data collection started"}
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to start data collection",
            context={"error": str(e)},
            cause=e
        )


@router.post("/stop", status_code=status.HTTP_200_OK)
async def stop_collection(
    service: DataCollectionService = Depends(get_service(DataCollectionService))
) -> dict:
    """Stop current data collection.
    
    Returns:
        Success response
        
    Raises:
        HTTPException: If collection cannot be stopped
    """
    try:
        await service.stop_collection()
        return {"message": "Data collection stopped"}
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to stop data collection",
            context={"error": str(e)},
            cause=e
        )


@router.post("/record", status_code=status.HTTP_200_OK)
async def record_event(
    x_pos: float,
    y_pos: float,
    z_pos: float,
    pressure: float,
    temperature: float,
    flow_rate: float,
    status: str = "active",
    service: DataCollectionService = Depends(get_service(DataCollectionService))
) -> dict:
    """Record a spray event.
    
    Args:
        x_pos: X position
        y_pos: Y position
        z_pos: Z position
        pressure: Gas pressure
        temperature: Gas temperature
        flow_rate: Powder flow rate
        status: Event status
        
    Returns:
        Success response
        
    Raises:
        HTTPException: If event cannot be recorded
    """
    try:
        await service.record_spray_event(
            x_pos=x_pos,
            y_pos=y_pos,
            z_pos=z_pos,
            pressure=pressure,
            temperature=temperature,
            flow_rate=flow_rate,
            status=status
        )
        return {"message": "Event recorded"}
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to record event",
            context={"error": str(e)},
            cause=e
        )


@router.get("/events/{sequence_id}", status_code=status.HTTP_200_OK)
async def get_events(
    sequence_id: str,
    service: DataCollectionService = Depends(get_service(DataCollectionService))
) -> List[SprayEvent]:
    """Get all events for a sequence.
    
    Args:
        sequence_id: ID of sequence to get events for
        
    Returns:
        List of spray events
        
    Raises:
        HTTPException: If events cannot be retrieved
    """
    try:
        return await service.get_sequence_events(sequence_id)
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to get events",
            context={"error": str(e)},
            cause=e
        )
