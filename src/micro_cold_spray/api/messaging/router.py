"""Messaging router."""

from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, status, Depends, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from .service import MessagingService
from ..config.singleton import get_config_service
from ..base.exceptions import ServiceError
from ..base.errors import AppErrorCode, format_error


class MessageResponse(BaseModel):
    """Message response model."""
    message_id: str
    topic: str
    timestamp: datetime


class ServiceResponse(BaseModel):
    """Standard service response model."""
    status: str
    message: str
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service_name: str
    version: str
    is_running: bool
    timestamp: datetime


# Create router with prefix (app will handle the base /api/v1 prefix)
router = APIRouter(prefix="/messaging", tags=["messaging"])

# Global service instance
_service: Optional[MessagingService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global _service
    try:
        # Get shared config service instance
        config_service = get_config_service()
        if not config_service.is_running:
            await config_service.start()
            if not config_service.is_running:
                raise ServiceError("ConfigService failed to start")
            logger.info("ConfigService started successfully")
        
        # Initialize messaging service
        _service = MessagingService(config_service=config_service)
        await _service.start()
        if not _service.is_running:
            raise ServiceError("MessagingService failed to start")
        logger.info("MessagingService started successfully")
        
        # Store service in app state for testing
        app.state.service = _service
        
        yield
        
    finally:
        # Cleanup on shutdown
        logger.info("Messaging API shutting down")
        if _service:
            try:
                await _service.stop()
                logger.info("Messaging service stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping messaging service: {e}")
            finally:
                _service = None
                app.state.service = None


# Create FastAPI app with lifespan
app = FastAPI(title="Messaging API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service() -> MessagingService:
    """Get service instance."""
    if not _service or not _service.is_running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, "MessagingService not initialized")
        )
    return _service


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not running"}
    }
)
async def health_check(service: MessagingService = Depends(get_service)):
    """Check service health."""
    try:
        # Directly check service health without storing result
        await service.check_health()
        return HealthResponse(
            status="ok" if service.is_running else "error",
            service_name=service._service_name,
            version=getattr(service, "version", "1.0.0"),
            is_running=service.is_running,
            timestamp=datetime.now()
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


@router.post(
    "/publish/{topic}",
    response_model=MessageResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid topic or message"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def publish_message(
    topic: str,
    message: Dict[str, Any],
    service: MessagingService = Depends(get_service)
) -> MessageResponse:
    """Publish a message to a topic."""
    try:
        message_id = await service.publish(topic, message)
        return MessageResponse(
            message_id=message_id,
            topic=topic,
            timestamp=datetime.now()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_error(AppErrorCode.INVALID_ACTION, str(e))
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error(AppErrorCode.SERVICE_ERROR, str(e))
        )


@router.websocket("/subscribe/{topic}")
async def subscribe_topic(websocket: WebSocket, topic: str, service: MessagingService = Depends(get_service)):
    """Subscribe to messages on a topic."""
    try:
        await websocket.accept()
        async for message in service.subscribe(topic):
            await websocket.send_json(message)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


# Include router in app
app.include_router(router, prefix="/api/v1")
