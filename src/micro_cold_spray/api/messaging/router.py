"""FastAPI router for messaging operations."""

from typing import Dict, Any, Optional, Set
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, BackgroundTasks, Request
from loguru import logger
import asyncio

from .service import MessagingService
from micro_cold_spray.api.base.exceptions import MessageError
from micro_cold_spray.api.base.router import add_health_endpoints
from ..config.singleton import get_config_service

# Create FastAPI app
app = FastAPI(title="Messaging API")
router = APIRouter(prefix="/messaging", tags=["messaging"])

# Add router to app
app.include_router(router)

_service: Optional[MessagingService] = None


@app.on_event("startup")
async def startup_event():
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
            
            # Add health endpoint directly to app
            add_health_endpoints(app, _service)
            logger.info("Messaging service started successfully")
        except Exception as e:
            logger.error(f"Failed to start messaging service: {e}")
            raise


@app.on_event("shutdown")
async def shutdown_event():
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


async def validate_topic(topic: str) -> None:
    """Validate topic name.
    
    Args:
        topic: Topic to validate
        
    Raises:
        HTTPException: If topic is invalid
    """
    if not topic or not topic.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid topic name", "topic": topic}
        )


@router.post("/publish/{topic}", response_model=Dict[str, Any])
async def publish_message(
    topic: str,
    data: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Publish message to topic.
    
    Args:
        topic: Topic to publish to
        data: Message data
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict containing operation status
        
    Raises:
        HTTPException: If message cannot be published
    """
    await validate_topic(topic)
    service = get_service()
    
    try:
        await service.publish(topic, data)
        background_tasks.add_task(logger.info, f"Published message to {topic}")
        
        return {
            "status": "published",
            "topic": topic,
            "timestamp": datetime.now().isoformat()
        }
    except MessageError as e:
        logger.error(f"Failed to publish message: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to publish message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/request/{topic}", response_model=Dict[str, Any])
async def send_request(
    topic: str,
    data: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Send request and get response.
    
    Args:
        topic: Topic to send request to
        data: Request data
        background_tasks: FastAPI background tasks
        
    Returns:
        Response data
        
    Raises:
        HTTPException: If request fails
    """
    await validate_topic(topic)
    service = get_service()
    
    try:
        response = await service.request(topic, data)
        background_tasks.add_task(logger.info, f"Sent request to {topic}")
        
        return {
            "status": "success",
            "topic": topic,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except MessageError as e:
        logger.error(f"Failed to send request: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to send request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.websocket("/subscribe/{topic}")
async def websocket_endpoint(websocket: WebSocket, topic: str):
    """Subscribe to topic via WebSocket.
    
    Args:
        websocket: WebSocket connection
        topic: Topic to subscribe to
    """
    try:
        await validate_topic(topic)
        service = get_service()
        
        # Accept connection
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for {topic}")
        
        # Setup message callback
        async def callback(data: Dict[str, Any]):
            try:
                await websocket.send_json({
                    "topic": topic,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {str(e)}")
                await websocket.close()
        
        # Subscribe to topic
        await service.subscribe(topic, callback)
        logger.info(f"Subscribed to {topic} via WebSocket")
        
        try:
            while True:
                # Keep connection alive and handle client messages
                data = await websocket.receive_json()
                logger.debug(f"Received WebSocket message: {data}")
                
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            
        finally:
            await websocket.close()
            logger.info(f"WebSocket connection closed for {topic}")
            
    except Exception as e:
        logger.error(f"WebSocket setup failed: {str(e)}")
        if websocket.client_state.connected:
            await websocket.close()


@router.get("/topics", response_model=Dict[str, Any])
async def get_topics() -> Dict[str, Any]:
    """Get list of valid topics.
    
    Returns:
        Dict containing topics list
        
    Raises:
        HTTPException: If topics cannot be retrieved
    """
    service = get_service()
    
    try:
        topics = await service.get_topics()
        return {
            "topics": list(topics),
            "count": len(topics),
            "timestamp": datetime.now().isoformat()
        }
    except MessageError as e:
        logger.error(f"Failed to get topics: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to get topics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/topics", response_model=Dict[str, Any])
async def set_topics(
    topics: Set[str],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Set valid topics.
    
    Args:
        topics: Set of valid topics
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict containing operation status
        
    Raises:
        HTTPException: If topics cannot be set
    """
    service = get_service()
    
    try:
        await service.set_valid_topics(topics)
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


@router.get("/topics/{topic}/subscribers", response_model=Dict[str, Any])
async def get_subscribers(topic: str) -> Dict[str, Any]:
    """Get subscribers for topic.
    
    Args:
        topic: Topic to get subscribers for
        
    Returns:
        Dict containing subscriber count
        
    Raises:
        HTTPException: If subscriber count cannot be retrieved
    """
    await validate_topic(topic)
    service = get_service()
    
    try:
        count = await service.get_subscriber_count(topic)
        return {
            "topic": topic,
            "subscriber_count": count,
            "timestamp": datetime.now().isoformat()
        }
    except MessageError as e:
        logger.error(f"Failed to get subscribers: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to get subscribers: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/control")
async def control_service(request: Request):
    """Control service operation."""
    data = await request.json()
    action = data.get("action")
    service = get_service()
    
    try:
        if action == "stop":
            await service.stop()
            return {"status": "stopped"}
        elif action == "start":
            await service.start()
            return {"status": "started"}
        elif action == "restart":
            await service.stop()
            await asyncio.sleep(1)
            await service.start()
            return {"status": "restarted"}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action: {action}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to {action} service: {str(e)}"
        )
