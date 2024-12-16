"""FastAPI router for data collection operations."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, FastAPI, Request, status
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from .service import DataCollectionService
from .models import SprayEvent
from .exceptions import DataCollectionError

# Create FastAPI app and router
app = FastAPI()
router = APIRouter(prefix="/data-collection", tags=["data-collection"])
_service: Optional[DataCollectionService] = None

# Mount router to app
app.include_router(router)


def init_router(service: DataCollectionService) -> None:
    """Initialize the router with a data collection service instance."""
    global _service
    _service = service


def get_service() -> DataCollectionService:
    """Get the data collection service instance."""
    if _service is None:
        logger.error("Data collection service not initialized")
        raise RuntimeError("Data collection service not initialized")
    return _service


async def validate_sequence(sequence_id: str) -> None:
    """Validate sequence ID format."""
    try:
        if not sequence_id or not sequence_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid sequence ID", "sequence_id": sequence_id}
            )
        
        # Additional sequence ID validation
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', sequence_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid sequence ID format",
                    "message": "Sequence ID must contain only alphanumeric characters, underscores, and hyphens"
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating sequence ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid sequence ID", "message": str(e)}
        )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": {
                "error": "Invalid parameters",
                "message": str(exc)
            }
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@router.post("/start", response_model=Dict[str, Any])
async def start_collection(
    sequence_id: str,
    collection_params: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Start data collection for a sequence."""
    try:
        await validate_sequence(sequence_id)
        
        # Validate collection parameters
        required_params = ['interval', 'duration']
        for param in required_params:
            if param not in collection_params:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Missing required parameter",
                        "message": f"Parameter '{param}' is required"
                    }
                )
            
        if collection_params['interval'] <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid collection parameters",
                    "message": "Collection interval must be positive"
                }
            )
        if collection_params['duration'] <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid collection parameters",
                    "message": "Collection duration must be positive"
                }
            )
            
        service = get_service()
        session = await service.start_collection(sequence_id, collection_params)
        background_tasks.add_task(logger.info, f"Started collection for {sequence_id}")
        
        return {
            "status": "started",
            "sequence_id": sequence_id,
            "start_time": session.start_time.isoformat(),
            "collection_params": session.collection_params
        }
    except HTTPException:
        raise
    except DataCollectionError as e:
        logger.error(f"Failed to start collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to start collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Failed to start collection", "message": str(e)}
        )


@router.post("/stop", response_model=Dict[str, Any])
async def stop_collection(
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Stop current data collection."""
    try:
        service = get_service()
        session = service.active_session
        
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to stop collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Failed to stop collection", "message": str(e)}
        )


@router.post("/events", response_model=Dict[str, Any])
async def record_event(
    event: SprayEvent,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Record a spray event."""
    try:
        await validate_sequence(event.sequence_id)
        service = get_service()
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
    except HTTPException:
        raise
    except DataCollectionError as e:
        logger.error(f"Failed to record event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "context": e.context}
        )
    except ValidationError as e:
        logger.error(f"Invalid event data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid event data", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to record event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Failed to record event", "message": str(e)}
        )


@router.get("/events/{sequence_id}", response_model=List[SprayEvent])
async def get_events(sequence_id: str) -> List[SprayEvent]:
    """Get all spray events for a sequence."""
    try:
        # Validate sequence ID format first
        import re
        if not sequence_id or not sequence_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid sequence ID", "sequence_id": sequence_id}
            )
        if not re.match(r'^[a-zA-Z0-9_-]+$', sequence_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid sequence ID format",
                    "message": "Sequence ID must contain only alphanumeric characters, underscores, and hyphens"
                }
            )
        
        service = get_service()
        events = await service.get_sequence_events(sequence_id)
        return events
    except HTTPException:
        raise
    except DataCollectionError as e:
        logger.error(f"Failed to get events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to get events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Failed to get events", "message": str(e)}
        )


@router.get("/status", response_model=Dict[str, Any])
async def get_collection_status() -> Dict[str, Any]:
    """Get current data collection status."""
    try:
        service = get_service()
        session = service.active_session
        
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
        return {
            "status": "inactive",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """Check service health."""
    try:
        service = get_service()
        storage_ok = await service.check_storage()
        
        response = {
            "service": "error" if not service.is_running else "ok",
            "storage": "error" if not storage_ok else "ok"
        }
        
        if not service.is_running or not storage_ok:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=response
            )
            
        return response
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "service": "error",
                "storage": "error",
                "error": str(e)
            }
        )
