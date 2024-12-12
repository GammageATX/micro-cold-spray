"""FastAPI router for messaging operations."""

from typing import Dict, Any, Optional, Set
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from .service import MessagingService
from .exceptions import MessagingError

router = APIRouter(prefix="/messaging", tags=["messaging"])
_service: Optional[MessagingService] = None


def init_router(service: MessagingService) -> None:
    """Initialize router with service instance.
    
    Args:
        service: Messaging service instance
    """
    global _service
    _service = service


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
    except MessagingError as e:
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
    except MessagingError as e:
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
    except MessagingError as e:
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
    except MessagingError as e:
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
    except MessagingError as e:
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


@router.get("/health")
async def health_check() -> JSONResponse:
    """Check API and service health status.
    
    Returns:
        JSON response with health status
        
    Note:
        Returns 503 if service unhealthy
    """
    service = get_service()
    
    try:
        status = {
            "service": "ok" if service.is_running else "error",
            "topics": len(service.get_topics()),
            "timestamp": datetime.now().isoformat()
        }
        
        if not service.is_running:
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
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
