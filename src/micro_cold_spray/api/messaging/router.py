from fastapi import APIRouter, HTTPException, WebSocket
from typing import Dict, Any, Optional, Set

from .service import MessagingService, MessagingError

router = APIRouter(prefix="/messaging", tags=["messaging"])
_service: Optional[MessagingService] = None

def init_router(service: MessagingService) -> None:
    """Initialize router with service instance."""
    global _service
    _service = service

def get_service() -> MessagingService:
    """Get messaging service instance."""
    if _service is None:
        raise RuntimeError("Messaging service not initialized")
    return _service

@router.post("/publish/{topic}")
async def publish_message(topic: str, data: Dict[str, Any]) -> Dict[str, str]:
    """Publish message to topic."""
    service = get_service()
    try:
        await service.publish(topic, data)
        return {"status": "published"}
    except MessagingError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/request/{topic}")
async def send_request(topic: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Send request and get response."""
    service = get_service()
    try:
        response = await service.request(topic, data)
        return response
    except MessagingError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.websocket("/subscribe/{topic}")
async def websocket_endpoint(websocket: WebSocket, topic: str):
    """Subscribe to topic via WebSocket."""
    service = get_service()
    await websocket.accept()
    
    async def callback(data: Dict[str, Any]):
        await websocket.send_json(data)
        
    try:
        await service.subscribe(topic, callback)
        while True:
            await websocket.receive_text()  # Keep connection alive
            
    except Exception:
        await websocket.close() 

@router.get("/topics")
async def get_topics() -> Dict[str, Any]:
    """Get list of valid topics."""
    service = get_service()
    try:
        topics = await service.get_topics()
        return {"topics": list(topics)}
    except MessagingError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/topics")
async def set_topics(topics: Set[str]) -> Dict[str, str]:
    """Set valid topics."""
    service = get_service()
    try:
        await service.set_valid_topics(topics)
        return {"status": "updated"}
    except MessagingError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/topics/{topic}/subscribers")
async def get_subscribers(topic: str) -> Dict[str, Any]:
    """Get subscribers for topic."""
    service = get_service()
    try:
        count = await service.get_subscriber_count(topic)
        return {"topic": topic, "subscriber_count": count}
    except MessagingError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/health")
async def health_check(
    service: MessagingService = Depends(get_service)
):
    """Check API health status."""
    try:
        # Check message broker connection
        queue_status = await service.get_queue_size() is not None
        if not queue_status:
            return {
                "status": "Error",
                "error": "Message queue error"
            }
        
        return {
            "status": "Running",
            "error": None
        }
    except Exception as e:
        return {
            "status": "Error",
            "error": str(e)
        } 