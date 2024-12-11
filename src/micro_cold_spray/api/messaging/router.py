"""FastAPI router for messaging operations."""

from fastapi import APIRouter, HTTPException, WebSocket, Depends
from typing import Dict, Any, Optional, Set
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
        raise RuntimeError("Messaging service not initialized")
    return _service


@router.post("/publish/{topic}")
async def publish_message(topic: str, data: Dict[str, Any]) -> Dict[str, str]:
    """Publish message to topic.
    
    Args:
        topic: Topic to publish to
        data: Message data
        
    Returns:
        Dictionary containing:
            - status: Operation status
            
    Raises:
        HTTPException: If message cannot be published
    """
    service = get_service()
    try:
        await service.publish(topic, data)
        return {"status": "published"}
    except MessagingError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to publish message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/request/{topic}")
async def send_request(topic: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Send request and get response.
    
    Args:
        topic: Topic to send request to
        data: Request data
        
    Returns:
        Response data
        
    Raises:
        HTTPException: If request fails
    """
    service = get_service()
    try:
        response = await service.request(topic, data)
        return response
    except MessagingError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to send request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.websocket("/subscribe/{topic}")
async def websocket_endpoint(websocket: WebSocket, topic: str):
    """Subscribe to topic via WebSocket.
    
    Args:
        websocket: WebSocket connection
        topic: Topic to subscribe to
    """
    service = get_service()
    await websocket.accept()
    
    async def callback(data: Dict[str, Any]):
        await websocket.send_json(data)
        
    try:
        await service.subscribe(topic, callback)
        while True:
            await websocket.receive_text()  # Keep connection alive
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()


@router.get("/topics")
async def get_topics() -> Dict[str, Any]:
    """Get list of valid topics.
    
    Returns:
        Dictionary containing:
            - topics: List of valid topics
            
    Raises:
        HTTPException: If topics cannot be retrieved
    """
    service = get_service()
    try:
        topics = await service.get_topics()
        return {"topics": list(topics)}
    except MessagingError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to get topics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/topics")
async def set_topics(topics: Set[str]) -> Dict[str, str]:
    """Set valid topics.
    
    Args:
        topics: Set of valid topics
        
    Returns:
        Dictionary containing:
            - status: Operation status
            
    Raises:
        HTTPException: If topics cannot be set
    """
    service = get_service()
    try:
        await service.set_valid_topics(topics)
        return {"status": "updated"}
    except MessagingError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to set topics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/topics/{topic}/subscribers")
async def get_subscribers(topic: str) -> Dict[str, Any]:
    """Get subscribers for topic.
    
    Args:
        topic: Topic to get subscribers for
        
    Returns:
        Dictionary containing:
            - topic: Topic name
            - subscriber_count: Number of subscribers
            
    Raises:
        HTTPException: If subscriber count cannot be retrieved
    """
    service = get_service()
    try:
        count = await service.get_subscriber_count(topic)
        return {"topic": topic, "subscriber_count": count}
    except MessagingError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "context": e.context}
        )
    except Exception as e:
        logger.error(f"Failed to get subscribers: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/health")
async def health_check(
    service: MessagingService = Depends(get_service)
) -> Dict[str, Any]:
    """Check API health status.
    
    Returns:
        Dictionary containing:
            - status: Service status
            - error: Error message if any
    """
    try:
        if not service.is_running:
            return {
                "status": "error",
                "message": "Service not running"
            }
            
        return {
            "status": "ok",
            "message": "Service healthy"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
