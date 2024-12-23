"""Messaging router."""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, status, Depends, WebSocket, Request, Body, HTTPException
from pydantic import BaseModel, Field
from loguru import logger
import uuid

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.ui.utils import get_uptime, get_memory_usage
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
    status: str = Field(..., description="Service status (ok or error)")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    is_running: bool = Field(..., description="Whether service is running")
    uptime: float = Field(..., description="Service uptime in seconds")
    memory_usage: Dict[str, float] = Field(..., description="Memory usage stats")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


# Create router with prefix
router = APIRouter(prefix="/messaging", tags=["messaging"])


def get_service(request: Request) -> MessagingService:
    """Get service instance."""
    return request.app.service


@router.post(
    "/publish/{topic:path}",
    response_model=MessageResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid topic or message"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def publish_message(
    topic: str,
    message: Dict[str, Any] = Body(...),
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
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Failed to publish message: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to publish message: {e}"
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
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                await websocket.close()
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Failed to send message: {e}"
                )
            
        # Subscribe to topic
        await service.subscribe(topic, message_handler)
        
        try:
            # Keep connection alive
            while True:
                await websocket.receive_text()
        except Exception:
            # Just log connection closure without raising - this is expected behavior
            logger.info(f"WebSocket connection closed for topic {topic}")
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
        if not isinstance(e, HTTPException):
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"WebSocket error: {e}"
            )
