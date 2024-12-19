"""Tag management endpoints."""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from datetime import datetime
from loguru import logger
from pydantic import BaseModel, Field

from ..models.tags import TagSubscription, TagMappingUpdateRequest
from ..service import CommunicationService
from ..dependencies import get_service
from ...base.exceptions import ServiceError, ValidationError


class TagResponse(BaseModel):
    """Tag response model."""
    status: str
    message: str
    timestamp: datetime


class TagValueResponse(BaseModel):
    """Tag value response model."""
    status: str
    tag_id: str
    value: Any
    timestamp: datetime


class TagListResponse(BaseModel):
    """Tag list response model."""
    status: str
    tags: List[Dict[str, Any]]
    timestamp: datetime


class WriteTagRequest(BaseModel):
    """Write tag request model."""
    tag_id: str = Field(..., description="Tag to write")
    value: Any = Field(..., description="Value to write")


router = APIRouter(prefix="/tags", tags=["tags"])


@router.websocket("/subscribe")
async def websocket_subscribe(
    websocket: WebSocket,
    service: CommunicationService = Depends(get_service(CommunicationService))
):
    """WebSocket endpoint for tag subscriptions."""
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Subscribe to all tag updates
        subscription_handler = None
        
        try:
            # Create a callback to send updates to the client
            async def send_update(tags: Dict[str, Any]):
                try:
                    await websocket.send_json({
                        "type": "update",
                        "tags": tags,
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Failed to send tag update: {e}")
            
            # Subscribe to tag updates
            subscription_handler = await service.tag_cache.subscribe(
                tags=None,  # None means all tags
                callback=send_update
            )
            
            # Send initial tag values
            initial_tags = await service.tag_cache.filter_tags()
            await websocket.send_json({
                "type": "tags",
                "tags": {
                    tag: value.value
                    for tag, value in initial_tags.tags.items()
                },
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep the connection alive
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close(code=1011)  # Internal error
        finally:
            if subscription_handler:
                await subscription_handler.stop()
                
    except Exception as e:
        logger.error(f"Failed to handle WebSocket connection: {e}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


@router.get(
    "/value/{tag_id}",
    response_model=TagValueResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Tag not found"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def get_tag_value(
    tag_id: str,
    service: CommunicationService = Depends(get_service)
):
    """Get tag value."""
    try:
        # Get tag value
        value = await service.tag_service.read_tag(tag_id)
        
        return TagValueResponse(
            status="ok",
            tag_id=tag_id,
            value=value,
            timestamp=datetime.now()
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/list",
    response_model=TagListResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def list_tags(service: CommunicationService = Depends(get_service)):
    """List available tags."""
    try:
        # Get tag list
        tag_list = await service.tag_service.list_tags()
        
        return TagListResponse(
            status="ok",
            tags=tag_list,
            timestamp=datetime.now()
        )
        
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/write",
    response_model=TagResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
        status.HTTP_404_NOT_FOUND: {"description": "Tag not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def write_tag_value(
    request: WriteTagRequest,
    service: CommunicationService = Depends(get_service)
):
    """Write tag value."""
    try:
        # Write tag value
        await service.tag_service.write_tag(
            tag_id=request.tag_id,
            value=request.value
        )
        
        return TagResponse(
            status="ok",
            message=f"Tag {request.tag_id} written with value {request.value}",
            timestamp=datetime.now()
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/subscribe/{tag_id}",
    response_model=TagResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Tag not found"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service error"}
    }
)
async def subscribe_to_tag(
    tag_id: str,
    service: CommunicationService = Depends(get_service)
):
    """Subscribe to tag updates."""
    try:
        # Subscribe to tag
        await service.tag_service.subscribe_to_tag(tag_id)
        
        return TagResponse(
            status="ok",
            message=f"Subscribed to tag {tag_id}",
            timestamp=datetime.now()
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/unsubscribe")
async def unsubscribe_from_tags(
    request: TagSubscription,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Unsubscribe from tag updates."""
    try:
        await service.tag_cache.unsubscribe(request.tags, request.callback_url)
        return {"status": "ok"}
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/mappings")
async def get_tag_mappings(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get tag mappings."""
    try:
        mappings = await service.tag_mapping.get_mappings()
        return {"mappings": mappings}
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/mappings")
async def update_tag_mapping(
    request: TagMappingUpdateRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Update tag mapping."""
    try:
        await service.tag_mapping.update_mapping(request.tag_path, request.plc_tag)
        return {"status": "ok"}
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/cache")
async def get_tag_cache(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get all cached tags and their values."""
    try:
        logger.debug("Getting tag cache service")
        tag_service = service.tag_cache
        logger.debug("Filtering tags")
        tag_cache = await tag_service.filter_tags()
        logger.debug(f"Found {len(tag_cache.tags)} tags")
        return {
            "tags": {
                tag: {
                    "value": value.value,
                    "metadata": value.metadata.dict(),
                    "timestamp": value.timestamp.isoformat()
                }
                for tag, value in tag_cache.tags.items()
            }
        }
    except ServiceError as e:
        logger.error(f"Service error in get_tag_cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in get_tag_cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
