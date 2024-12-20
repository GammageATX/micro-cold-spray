"""Messaging router."""

from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, status, Depends, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger
import uuid

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config import get_config_service
from .messaging_service import MessagingService


class MessageResponse(BaseModel):
    """Message response model."""
    message_id: str = Field(..., description="Unique message ID")
    topic: str = Field(..., description="Message topic")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")


class ServiceResponse(BaseModel):
    """Standard service response model."""
    status: str = Field(..., description="Service status")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    is_running: bool = Field(..., description="Whether service is running")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


# Create router with prefix
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
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="ConfigService failed to start"
                )
            logger.info("ConfigService started successfully")
        
        # Initialize messaging service
        _service = MessagingService(config_service=config_service)
        await _service.start()
        if not _service.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="MessagingService failed to start"
            )
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
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="MessagingService not initialized"
        )
    return _service


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not running"}
    }
)
async def health_check(service: MessagingService = Depends(get_service)) -> HealthResponse:
    """Check service health."""
    try:
        health = await service.check_health()
        return HealthResponse(
            status=health["status"],
            service_name=service.name,
            version=getattr(service, "version", "1.0.0"),
            is_running=service.is_running,
            timestamp=datetime.now()
        )
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Health check failed",
            context={"error": str(e)},
            cause=e
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
        await service.publish(topic, message)
        return MessageResponse(
            message_id=str(uuid.uuid4()),
            topic=topic,
            timestamp=datetime.now()
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to publish message",
            context={"error": str(e), "topic": topic},
            cause=e
        )


@router.websocket("/subscribe/{topic}")
async def subscribe_topic(
    websocket: WebSocket,
    topic: str,
    service: MessagingService = Depends(get_service)
):
    """Subscribe to messages on a topic."""
    try:
        await websocket.accept()
        
        # Create message handler
        async def message_handler(data: Dict[str, Any]):
            await websocket.send_json(data)
            
        # Subscribe to topic
        await service.subscribe(topic, message_handler)
        
        try:
            # Keep connection alive
            while True:
                await websocket.receive_text()
        except Exception:
            logger.info(f"WebSocket connection closed for topic {topic}")
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


# Include router in app
app.include_router(router, prefix="/api/v1")
