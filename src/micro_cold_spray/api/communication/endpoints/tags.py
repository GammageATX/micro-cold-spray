"""Tag management endpoints."""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from datetime import datetime
from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.models.tags import TagSubscription, TagMappingUpdateRequest
from micro_cold_spray.api.communication.communication_service import CommunicationService
from micro_cold_spray.api.communication.dependencies import get_service


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
        logger.debug(f"Reading value for tag {tag_id}")
        # Get tag value
        value = await service.tag_service.read_tag(tag_id)
        
        return TagValueResponse(
            status="ok",
            tag_id=tag_id,
            value=value,
            timestamp=datetime.now()
        )
        
    except ValueError as e:
        error_msg = f"Tag {tag_id} not found"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message=error_msg,
            context={"tag_id": tag_id},
            cause=e
        )
    except ConnectionError as e:
        error_msg = f"Tag service error reading tag {tag_id}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg,
            context={"tag_id": tag_id},
            cause=e
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        error_msg = f"Unexpected error reading tag {tag_id}"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg,
            context={"tag_id": tag_id},
            cause=e
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
        logger.debug("Listing available tags")
        # Get tag list
        tag_list = await service.tag_service.list_tags()
        
        return TagListResponse(
            status="ok",
            tags=tag_list,
            timestamp=datetime.now()
        )
        
    except ConnectionError as e:
        error_msg = "Tag service error listing tags"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg,
            cause=e
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        error_msg = "Unexpected error listing tags"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg,
            cause=e
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
        logger.debug(f"Writing value {request.value} to tag {request.tag_id}")
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
        error_msg = f"Invalid write parameters for tag {request.tag_id}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=error_msg,
            context={"request": request.dict()},
            cause=e
        )
    except ConnectionError as e:
        error_msg = f"Tag service error writing to tag {request.tag_id}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg,
            context={"request": request.dict()},
            cause=e
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        error_msg = f"Unexpected error writing to tag {request.tag_id}"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg,
            context={"request": request.dict()},
            cause=e
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
        logger.debug(f"Subscribing to tag {tag_id}")
        # Subscribe to tag
        await service.tag_service.subscribe_to_tag(tag_id)
        
        return TagResponse(
            status="ok",
            message=f"Subscribed to tag {tag_id}",
            timestamp=datetime.now()
        )
        
    except ValueError as e:
        error_msg = f"Tag {tag_id} not found"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_404_NOT_FOUND,
            message=error_msg,
            context={"tag_id": tag_id},
            cause=e
        )
    except ConnectionError as e:
        error_msg = f"Tag service error subscribing to tag {tag_id}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg,
            context={"tag_id": tag_id},
            cause=e
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        error_msg = f"Unexpected error subscribing to tag {tag_id}"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg,
            context={"tag_id": tag_id},
            cause=e
        )


@router.post("/unsubscribe")
async def unsubscribe_from_tags(
    request: TagSubscription,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Unsubscribe from tag updates."""
    try:
        logger.debug(f"Unsubscribing from tags: {request.tags}")
        await service.tag_cache.unsubscribe(request.tags, request.callback_url)
        return {"status": "ok"}
    except ValidationError as e:
        error_msg = "Invalid unsubscribe parameters"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=error_msg,
            context={"request": request.dict()},
            cause=e
        )
    except ConnectionError as e:
        error_msg = "Tag service error unsubscribing from tags"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg,
            context={"request": request.dict()},
            cause=e
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        error_msg = "Unexpected error unsubscribing from tags"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg,
            context={"request": request.dict()},
            cause=e
        )


@router.get("/mappings")
async def get_tag_mappings(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get tag mappings."""
    try:
        logger.debug("Getting tag mappings")
        mappings = await service.tag_mapping.get_mappings()
        return {"mappings": mappings}
    except ValidationError as e:
        error_msg = "Invalid mapping request"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=error_msg,
            cause=e
        )
    except ConnectionError as e:
        error_msg = "Tag service error getting mappings"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg,
            cause=e
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        error_msg = "Unexpected error getting tag mappings"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg,
            cause=e
        )


@router.post("/mappings")
async def update_tag_mapping(
    request: TagMappingUpdateRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Update tag mapping."""
    try:
        logger.debug(f"Updating mapping for tag {request.tag_path}")
        await service.tag_mapping.update_mapping(request.tag_path, request.plc_tag)
        return {"status": "ok"}
    except ValidationError as e:
        error_msg = "Invalid mapping parameters"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=error_msg,
            context={"request": request.dict()},
            cause=e
        )
    except ConnectionError as e:
        error_msg = "Tag service error updating mapping"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg,
            context={"request": request.dict()},
            cause=e
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        error_msg = "Unexpected error updating tag mapping"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg,
            context={"request": request.dict()},
            cause=e
        )


@router.get("/cache")
async def get_tag_cache(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get all cached tags and their values."""
    try:
        logger.debug("Getting tag cache")
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
    except ConnectionError as e:
        error_msg = "Tag service error getting cache"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg,
            cause=e
        )
    except Exception as e:
        if isinstance(e, create_error):
            raise e
        error_msg = "Unexpected error getting tag cache"
        logger.error(f"{error_msg}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg,
            cause=e
        )
