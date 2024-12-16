"""FastAPI router for messaging operations."""

from typing import Dict, Any, Optional, Set
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, BackgroundTasks, Body
from starlette.websockets import WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel

from .service import MessagingService
from micro_cold_spray.api.base.exceptions import MessageError
from ..config.singleton import get_config_service


class MessageData(BaseModel):
    """Message data model."""
    key: str
    value: Any


# Create router with prefix
router = APIRouter(prefix="/messaging", tags=["messaging"])

_service: Optional[MessagingService] = None


@router.on_event("startup")
async def startup():
    """Handle startup tasks."""
    logger.info("Messaging API starting up")
    global _service
    if _service is None:
        try:
            # Get shared config service instance
            config_service = get_config_service()
            await config_service.start()
            logger.info("ConfigService started successfully")
            
            # Create messaging service with config
            _service = MessagingService(config_service=config_service)
            await _service.start()
            logger.info("Messaging service started successfully")
        except Exception as e:
            logger.error(f"Failed to start messaging service: {e}")
            raise


@router.on_event("shutdown")
async def shutdown():
    """Handle shutdown tasks."""
    logger.info("Messaging API shutting down")
    if _service:
        try:
            await _service.stop()
            logger.info("Messaging service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping messaging service: {e}")


def get_service() -> MessagingService:
    """Get messaging service instance.
    
    Returns:
        MessagingService instance
        
    Raises:
        RuntimeError: If service not initialized
    """
    if _service is None:
        logger.error("Messaging service not initialized")
        raise RuntimeError("Messaging service not initialized")
    return _service


@router.get("/health")
async def health_check():
    """Check messaging service health."""
    try:
        service = get_service()
        return await service.check_health()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def get_topics():
    """Get list of available topics."""
    try:
        service = get_service()
        topics = await service.get_topics()
        return {"topics": list(topics)}
    except Exception as e:
        logger.error(f"Failed to get topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscribers/{topic:path}")
async def get_subscriber_count(topic: str):
    """Get subscriber count for a topic."""
    service = get_service()
    try:
        count = await service.get_subscriber_count(topic)
        return {"count": count}
    except MessageError as e:
        raise HTTPException(status_code=400, detail={"error": str(e), **e.details})


async def validate_topic(topic: str) -> None:
    """Validate topic name.
    
    Args:
        topic: Topic to validate
        
    Raises:
        HTTPException: If topic is invalid
    """
    if topic.isspace():  # Whitespace-only topics are invalid
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid topic name", "topic": topic}
        )


@router.post("/publish/")
async def publish_message_empty():
    """Handle empty topic publish attempts."""
    raise HTTPException(
        status_code=404,
        detail={"error": "Topic not found", "topic": ""}
    )


@router.post("/publish/{topic:path}")
async def publish_message(topic: str, message: Dict[str, Any] = Body(...)):
    """Publish a message to a topic."""
    if not topic:  # Empty path should be handled by publish_message_empty
        raise HTTPException(
            status_code=404,
            detail={"error": "Topic not found", "topic": topic}
        )
    
    await validate_topic(topic)  # Validate non-empty topics
    
    service = get_service()
    try:
        await service.publish(topic, message)
        return {
            "status": "published",
            "topic": topic,
            "timestamp": datetime.now().isoformat()
        }
    except MessageError as e:
        raise HTTPException(status_code=400, detail={"error": str(e), **e.details})


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
        raise HTTPException(status_code=400, detail={"error": str(e), **e.details})


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
            await websocket.close(code=1000, reason=str(e))
            raise WebSocketDisconnect(code=1000)
            
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
            await websocket.close(code=1000)
        except Exception:
            pass  # Ignore errors during close
        raise WebSocketDisconnect(code=1000)


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
        logger.error(f"Failed to set topics: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to set topics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/control")
async def control_service(
    data: Dict[str, Any] = Body(...),
    background_tasks: BackgroundTasks = None
):
    """Control messaging service."""
    service = get_service()
    action = data.get("action")
    
    if not action:
        raise HTTPException(
            status_code=400,
            detail={"error": "Missing action", "valid_actions": ["start", "stop", "restart"]}
        )
    
    valid_actions = ["start", "stop", "restart"]
    if action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid action", "valid_actions": valid_actions}
        )
    
    try:
        if action == "stop":
            await service.stop()
            status = "stopped"
        elif action == "start":
            await service.start()
            status = "started"
        elif action == "restart":
            await service.stop()
            await service.start()
            status = "restarted"
        
        if background_tasks:
            background_tasks.add_task(logger.info, f"Service {status}")
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Service control failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )
