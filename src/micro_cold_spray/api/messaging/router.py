"""FastAPI router for messaging operations."""

from typing import Dict, Any, Optional, Set
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, WebSocket, BackgroundTasks, Body, FastAPI
from starlette.websockets import WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from .service import MessagingService
from micro_cold_spray.api.base.exceptions import MessageError
from ..base.errors import ErrorCode, format_error
from ..config.singleton import get_config_service
from micro_cold_spray.api.base.router import add_health_endpoints


class MessageData(BaseModel):
    """Message data model."""
    key: str
    value: Any


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI."""
    global _service
    try:
        # Get shared config service instance
        config_service = get_config_service()
        await config_service.start()
        logger.info("ConfigService started successfully")
        
        # Create messaging service with config service
        _service = MessagingService(config_service=config_service)
        await _service.start()
        logger.info("Messaging service started successfully")
        
        # Add health endpoints
        add_health_endpoints(app, _service)
        yield
    finally:
        if _service:
            await _service.stop()
            logger.info("Messaging service stopped successfully")


# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create router with prefix
router = APIRouter(prefix="/messaging", tags=["messaging"])

# Include router in app
app.include_router(router)

_service: Optional[MessagingService] = None


def init_router(service_instance: MessagingService) -> None:
    """Initialize router with service instance.
    
    Args:
        service_instance: MessagingService instance to use
    """
    global _service
    _service = service_instance


def get_service() -> MessagingService:
    """Get messaging service instance."""
    if _service is None:
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, "Messaging service not initialized")["detail"]
        )
    return _service


@router.get("/health")
async def health_check():
    """Check messaging service health."""
    try:
        service = get_service()
        return await service.check_health()
    except Exception as e:
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )


@router.get("/topics")
async def get_topics():
    """Get list of available topics."""
    try:
        service = get_service()
        topics = await service.get_topics()
        return {"topics": list(topics)}
    except Exception as e:
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )


@router.get("/subscribers/{topic:path}")
async def get_subscriber_count(topic: str):
    """Get subscriber count for a topic."""
    service = get_service()
    try:
        count = await service.get_subscriber_count(topic)
        return {"count": count}
    except MessageError as e:
        error = ErrorCode.BAD_REQUEST
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e), e.context)["detail"]
        )


async def validate_topic(topic: str) -> None:
    """Validate topic name."""
    if topic.isspace():
        error = ErrorCode.INVALID_ACTION
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, "Invalid topic name", {"topic": topic})["detail"]
        )


@router.post("/publish/")
async def publish_message_empty():
    """Handle empty topic publish attempts."""
    error = ErrorCode.NOT_FOUND
    raise HTTPException(
        status_code=error.get_status_code(),
        detail=format_error(error, "Topic not found", {"topic": ""})["detail"]
    )


@router.post("/publish/{topic:path}")
async def publish_message(topic: str, message: Dict[str, Any] = Body(...)):
    """Publish a message to a topic."""
    if not topic:
        error = ErrorCode.NOT_FOUND
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, "Topic not found", {"topic": topic})["detail"]
        )
    
    await validate_topic(topic)
    
    service = get_service()
    try:
        await service.publish(topic, message)
        return {
            "status": "published",
            "topic": topic,
            "timestamp": datetime.now().isoformat()
        }
    except MessageError as e:
        error = ErrorCode.BAD_REQUEST
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e), e.context)["detail"]
        )


@router.post("/request/{topic:path}")
async def request_message(topic: str, message: Dict[str, Any] = Body(...)):
    """Send a request-response message."""
    service = get_service()
    try:
        response = await service.request(topic, message)
        return {
            "status": "success",
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except MessageError as e:
        error = ErrorCode.BAD_REQUEST
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e), e.context)["detail"]
        )


@router.websocket("/subscribe/{topic:path}")
async def websocket_subscribe(websocket: WebSocket, topic: str):
    """Subscribe to a topic via WebSocket."""
    service = get_service()
    handler = None
    
    try:
        await websocket.accept()
        
        # Subscribe to topic
        try:
            handler = await service.subscribe(topic, lambda msg: websocket.send_json(msg))
        except MessageError as e:
            logger.error(f"WebSocket subscription error: {e}")
            await websocket.close(code=1008, reason=str(e))  # Policy violation
            raise WebSocketDisconnect(code=1008)
            
        # Main message loop
        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "subscribe":
                    await websocket.send_json({
                        "type": "subscribed",
                        "topic": topic,
                        "timestamp": datetime.now().isoformat()
                    })
                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for topic: {topic}")
        except Exception as e:
            logger.error(f"WebSocket error in message loop: {e}")
        finally:
            if handler:
                await handler.stop()
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1008)  # Policy violation
        except Exception:
            pass  # Ignore errors during close
        raise WebSocketDisconnect(code=1008)


@router.post("/control")
async def control_service(
    data: Dict[str, Any] = Body(...),
    background_tasks: BackgroundTasks = None
):
    """Control messaging service."""
    service = get_service()
    action = data.get("action")

    if not action:
        error = ErrorCode.MISSING_PARAMETER
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, "Missing action", {"valid_actions": ["start", "stop", "restart"]})["detail"]
        )

    valid_actions = ["start", "stop", "restart"]
    if action not in valid_actions:
        error = ErrorCode.INVALID_ACTION
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, "Invalid action", {"valid_actions": valid_actions})["detail"]
        )

    try:
        if action == "stop":
            await service.stop()
            return {"status": "stopped"}
        elif action == "start":
            await service.start()
            return {"status": "started"}
        elif action == "restart":
            await service.stop()
            await service.start()
            return {"status": "restarted"}
    except Exception as e:
        error = ErrorCode.INTERNAL_ERROR
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e))["detail"]
        )


@router.post("/topics")
async def set_topics(
    topics: Set[str] = Body(...),
    background_tasks: BackgroundTasks = None
):
    """Set valid topics."""
    service = get_service()
    
    try:
        await service.set_valid_topics(topics)
        if background_tasks:
            background_tasks.add_task(logger.info, f"Updated valid topics: {topics}")
        
        return {
            "status": "updated",
            "topics": list(topics),
            "count": len(topics),
            "timestamp": datetime.now().isoformat()
        }
    except MessageError as e:
        error = ErrorCode.BAD_REQUEST
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, str(e), e.context)["detail"]
        )
