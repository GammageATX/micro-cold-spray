"""Messaging router."""

from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, status, Depends, WebSocket
from pydantic import BaseModel
from loguru import logger

from micro_cold_spray.core.messaging.services.service import MessagingService
from micro_cold_spray.core.config.utils.singleton import get_config_service
from micro_cold_spray.core.errors.exceptions import ServiceError
from micro_cold_spray.core.errors.codes import AppErrorCode
from micro_cold_spray.core.errors.formatting import format_error
from micro_cold_spray.core.base import create_service_dependency


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


# Create dependency for MessagingService
get_messaging_service = create_service_dependency(MessagingService)


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
    service: MessagingService = Depends(get_messaging_service)
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
async def subscribe_topic(websocket: WebSocket, topic: str, service: MessagingService = Depends(get_messaging_service)):
    """Subscribe to messages on a topic."""
    try:
        await websocket.accept()
        async for message in service.subscribe(topic):
            await websocket.send_json(message)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
