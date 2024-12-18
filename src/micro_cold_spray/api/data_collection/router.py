"""FastAPI router for data collection operations."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, BackgroundTasks, FastAPI, Request, status, Query, Body, Path
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel, Field

from .service import DataCollectionService
from .storage import DatabaseStorage
from .models import SprayEvent
from .exceptions import DataCollectionError
from ..base.router import add_health_endpoints
from ..config.singleton import get_config_service

# Create router without prefix (app already handles the /data-collection prefix)
router = APIRouter(tags=["data-collection"])
_service: Optional[DataCollectionService] = None

__all__ = ["router", "init_router", "app"]


def init_router(service: DataCollectionService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global _service
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Get database configuration
        config = await config_service.get_config("application")
        db_config = config.data.get("services", {}).get("data_collection", {}).get("database", {})
        dsn = f"postgresql://{db_config.get('user', 'postgres')}:{db_config.get('password', 'dbpassword')}@{db_config.get('host', 'localhost')}:{db_config.get('port', 5432)}/{db_config.get('database', 'micro_cold_spray')}"
        
        # Initialize storage backend
        storage = DatabaseStorage(dsn=dsn)
        await storage.initialize()
        logger.info("Database storage initialized successfully")
        
        # Initialize data collection service
        _service = DataCollectionService(storage=storage, config_service=config_service)
        await _service.start()
        logger.info("DataCollectionService started successfully")
        
        # Add health endpoints
        add_health_endpoints(app, _service)
        # Mount router to app
        app.include_router(router)
        logger.info("Data collection router initialized")
        
        yield
        
        # Cleanup on shutdown
        logger.info("Data collection API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("Data collection service stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping data collection service: {e}")
            finally:
                _service = None
            
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Attempt cleanup
        if _service and _service.is_running:
            await _service.stop()
            _service = None
        raise


# Create FastAPI app with lifespan
app = FastAPI(title="Data Collection API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service() -> DataCollectionService:
    """Get the data collection service instance."""
    if _service is None:
        logger.error("Data collection service not initialized")
        raise RuntimeError("Data collection service not initialized")
    return _service


class CollectionParameters(BaseModel):
    """Collection parameters validation model."""
    interval: float = Field(gt=0, description="Collection interval in seconds")
    duration: float = Field(gt=0, description="Collection duration in seconds")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@router.post("/start", response_model=Dict[str, Any])
async def start_collection(
    background_tasks: BackgroundTasks,
    sequence_id: str = Query(
        ...,
        pattern="^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=100,
        description="Collection sequence identifier"
    ),
    collection_params: CollectionParameters = Body(..., description="Collection parameters")
) -> Dict[str, Any]:
    """Start data collection for a sequence."""
    try:
        service = get_service()
        session = await service.start_collection(sequence_id, collection_params.model_dump())
        background_tasks.add_task(logger.info, f"Started collection for {sequence_id}")
        
        return {
            "status": "started",
            "sequence_id": sequence_id,
            "start_time": session.start_time.isoformat(),
            "collection_params": session.collection_params
        }
    except DataCollectionError as e:
        logger.error(f"Failed to start collection: {str(e)}")
        if "Collection already in progress" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": str(e), "context": e.context}
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to start collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "No active collection session to stop"}
            )
        
        await service.stop_collection()
        background_tasks.add_task(
            logger.info,
            f"Stopped collection for {session.sequence_id}"
        )
        return {"status": "stopped"}
    except DataCollectionError as e:
        logger.error(f"Failed to stop collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "context": e.context}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to stop collection", "message": str(e)}
        )


@router.post("/events", response_model=Dict[str, Any])
async def record_event(
    background_tasks: BackgroundTasks,
    event: SprayEvent = Body(..., description="Spray event to record")
) -> Dict[str, Any]:
    """Record a spray event."""
    try:
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
    except DataCollectionError as e:
        logger.error(f"Failed to record event: {str(e)}")
        if "Duplicate spray event" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": str(e), "context": e.context}
            )
        if "No active collection session" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": str(e), "context": e.context}
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to record event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to record event", "message": str(e)}
        )


@router.get("/events/{sequence_id}", response_model=List[SprayEvent])
async def get_events(
    sequence_id: str = Path(
        ...,
        pattern="^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=100,
        description="Collection sequence identifier"
    )
) -> List[SprayEvent]:
    """Get all spray events for a sequence."""
    try:
        service = get_service()
        events = await service.get_sequence_events(sequence_id)
        if not events:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"No events found for sequence {sequence_id}"}
            )
        return events
    except DataCollectionError as e:
        logger.error(f"Failed to get events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "context": e.context}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
        )


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
