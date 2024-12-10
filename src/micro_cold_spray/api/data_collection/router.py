"""FastAPI router for data collection operations."""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException

from .service import DataCollectionService, DataCollectionError

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