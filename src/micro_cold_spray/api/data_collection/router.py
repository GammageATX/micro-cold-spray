"""FastAPI router for data collection operations."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from .service import DataCollectionService
from .models import SprayEvent
from .exceptions import DataCollectionError

router = APIRouter(prefix="/data-collection", tags=["data-collection"])
_service: Optional[DataCollectionService] = None


def init_router(service: DataCollectionService) -> None:
    """Initialize the router with a data collection service instance."""
    global _service
    _service = service


def get_service() -> DataCollectionService:
    """Get the data collection service instance.
    
    Returns:
        DataCollectionService instance
        
    Raises:
        RuntimeError: If service not initialized
    """
    if _service is None:
        logger.error("Data collection service not initialized")
        raise RuntimeError("Data collection service not initialized")
    return _service


async def validate_sequence(sequence_id: str) -> None:
    """Validate sequence ID format.
    
    Args:
        sequence_id: Sequence ID to validate
        
    Raises:
        HTTPException: If sequence ID is invalid
    """
    if not sequence_id or not sequence_id.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid sequence ID", "sequence_id": sequence_id}
        )


@router.post("/start", response_model=Dict[str, Any])
async def start_collection(
    sequence_id: str,
    collection_params: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Start data collection for a sequence.
    
    Args:
        sequence_id: ID of sequence to collect data for
        collection_params: Parameters for data collection
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict containing operation status and session info
        
    Raises:
        HTTPException: If operation fails
    """
    await validate_sequence(sequence_id)
    service = get_service()
    
    try:
        session = await service.start_collection(sequence_id, collection_params)
        background_tasks.add_task(logger.info, f"Started collection for {sequence_id}")
        
        return {
            "status": "started",
            "sequence_id": sequence_id,
            "start_time": session.start_time.isoformat(),
            "collection_params": session.collection_params
        }
    except DataCollectionError as e:
        logger.error(f"Failed to start collection: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to start collection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/stop", response_model=Dict[str, Any])
async def stop_collection(
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Stop current data collection.
    
    Args:
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict containing operation status
        
    Raises:
        HTTPException: If operation fails
    """
    service = get_service()
    session = service.active_session
    
    try:
        await service.stop_collection()
        if session:
            background_tasks.add_task(
                logger.info,
                f"Stopped collection for {session.sequence_id}"
            )
        return {"status": "stopped"}
    except DataCollectionError as e:
        logger.error(f"Failed to stop collection: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to stop collection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/events", response_model=Dict[str, Any])
async def record_event(
    event: SprayEvent,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Record a spray event.
    
    Args:
        event: The spray event to record
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict containing operation status
        
    Raises:
        HTTPException: If operation fails
    """
    await validate_sequence(event.sequence_id)
    service = get_service()
    
    try:
        await service.record_spray_event(event)
        background_tasks.add_task(
            logger.debug,
            f"Recorded event {event.spray_index} for {event.sequence_id}"
        )
        return {
            "status": "recorded",
            "sequence_id": event.sequence_id,
            "spray_index": event.spray_index,
            "timestamp": event.timestamp.isoformat()
        }
    except DataCollectionError as e:
        logger.error(f"Failed to record event: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to record event: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/events/{sequence_id}", response_model=List[SprayEvent])
async def get_events(sequence_id: str) -> List[SprayEvent]:
    """Get all spray events for a sequence.
    
    Args:
        sequence_id: ID of sequence to get events for
        
    Returns:
        List of spray events
        
    Raises:
        HTTPException: If operation fails
    """
    await validate_sequence(sequence_id)
    service = get_service()
    
    try:
        events = await service.get_sequence_events(sequence_id)
        return events
    except DataCollectionError as e:
        logger.error(f"Failed to get events: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to get events: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/status", response_model=Dict[str, Any])
async def get_collection_status() -> Dict[str, Any]:
    """Get current data collection status.
    
    Returns:
        Dict containing collection status
        
    Raises:
        HTTPException: If operation fails
    """
    service = get_service()
    session = service.active_session
    
    try:
        if not session:
            return {
                "status": "inactive",
                "last_check": datetime.now().isoformat()
            }
            
        return {
            "status": "active",
            "sequence_id": session.sequence_id,
            "start_time": session.start_time.isoformat(),
            "collection_params": session.collection_params,
            "last_check": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.get("/health")
async def health_check() -> JSONResponse:
    """Check API and storage health status.
    
    Returns:
        JSON response with health status
        
    Note:
        Returns 503 if service unhealthy
    """
    service = get_service()
    
    try:
        storage_ok = await service.check_storage()
        service_ok = service.is_running
        
        status = {
            "service": "ok" if service_ok else "error",
            "storage": "ok" if storage_ok else "error",
            "timestamp": datetime.now().isoformat()
        }
        
        if not (service_ok and storage_ok):
            return JSONResponse(
                status_code=503,
                content=status
            )
            
        return JSONResponse(status)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "service": "error",
                "storage": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
