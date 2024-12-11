"""FastAPI router for data collection operations."""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends

from .service import DataCollectionService, DataCollectionError, SprayEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-collection", tags=["data-collection"])
_service: Optional[DataCollectionService] = None


def init_router(service: DataCollectionService) -> None:
    """Initialize the router with a data collection service instance."""
    global _service
    _service = service


def get_service() -> DataCollectionService:
    """Get the data collection service instance."""
    if _service is None:
        raise RuntimeError("Data collection service not initialized")
    return _service


@router.post("/start")
async def start_collection(sequence_id: str, collection_params: Dict[str, Any]) -> Dict[str, str]:
    """
    Start data collection for a sequence.
    
    Args:
        sequence_id: ID of sequence to collect data for
        collection_params: Parameters for data collection
        
    Returns:
        Dict containing operation status
    """
    service = get_service()
    try:
        await service.start_collection(sequence_id, collection_params)
        return {
            "status": "started",
            "sequence_id": sequence_id
        }
    except DataCollectionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to start data collection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/stop")
async def stop_collection() -> Dict[str, str]:
    """
    Stop current data collection.
    
    Returns:
        Dict containing operation status
    """
    service = get_service()
    try:
        await service.stop_collection()
        return {"status": "stopped"}
    except DataCollectionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to stop data collection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/events")
async def record_event(event: SprayEvent) -> Dict[str, str]:
    """
    Record a spray event.
    
    Args:
        event: The spray event to record
        
    Returns:
        Dict containing operation status
    """
    service = get_service()
    try:
        await service.record_spray_event(event)
        return {
            "status": "recorded",
            "spray_index": event.spray_index
        }
    except DataCollectionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to record spray event: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/events/{sequence_id}")
async def get_events(sequence_id: str) -> List[SprayEvent]:
    """
    Get all spray events for a sequence.
    
    Args:
        sequence_id: ID of sequence to get events for
        
    Returns:
        List of spray events
    """
    service = get_service()
    try:
        return await service.get_sequence_events(sequence_id)
    except DataCollectionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to get sequence events: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/status")
async def get_collection_status() -> Dict[str, Any]:
    """
    Get current data collection status.
    
    Returns:
        Dict containing collection status
    """
    service = get_service()
    session = service.active_session
    
    if not session:
        return {"status": "inactive"}
        
    return {
        "status": "active",
        "sequence_id": session.sequence_id,
        "start_time": session.start_time.isoformat(),
        "collection_params": session.collection_params
    }


@router.get("/health")
async def health_check(
    service: DataCollectionService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Check API health status.
    
    Returns:
        Dict containing health status
    """
    try:
        storage_ok = await service.check_storage()
        if not storage_ok:
            return {
                "status": "error",
                "message": "Storage check failed"
            }
        
        return {
            "status": "ok",
            "message": "Service healthy"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
