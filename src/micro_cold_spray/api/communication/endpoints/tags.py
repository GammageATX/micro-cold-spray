"""Tag management endpoints."""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from datetime import datetime
from loguru import logger

from ..models.tags import TagSubscription, TagUpdate, TagMappingUpdateRequest
from ..service import CommunicationService
from ...base import get_service
from ...base.exceptions import ServiceError, ValidationError
from ...base.errors import ErrorCode, format_error

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


@router.get("/values")
async def get_tag_values(
    tags: str,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get tag values."""
    try:
        tag_list = [tag.strip() for tag in tags.split(",")]
        values = await service.tag_cache.get_values(tag_list)
        return {"values": values}
    except ValidationError as e:
        raise HTTPException(
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
        )


@router.post("/write")
async def write_tag_value(
    request: TagUpdate,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Write tag value."""
    try:
        await service.tag_cache.write_value(request.tag, request.value)
        return {"status": "ok"}
    except ValidationError as e:
        raise HTTPException(
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
        )


@router.post("/subscribe")
async def subscribe_to_tags(
    request: TagSubscription,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Subscribe to tag updates."""
    try:
        await service.tag_cache.subscribe(request.tags, request.callback_url)
        return {"status": "ok"}
    except ValidationError as e:
        raise HTTPException(
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
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
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
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
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
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
            status_code=ErrorCode.VALIDATION_ERROR.get_status_code(),
            detail=format_error(ErrorCode.VALIDATION_ERROR, str(e), e.context)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
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
            status_code=ErrorCode.SERVICE_UNAVAILABLE.get_status_code(),
            detail=format_error(ErrorCode.SERVICE_UNAVAILABLE, str(e), e.context)
        )
    except Exception as e:
        logger.error(f"Error in get_tag_cache: {e}")
        raise HTTPException(
            status_code=ErrorCode.INTERNAL_ERROR.get_status_code(),
            detail=format_error(ErrorCode.INTERNAL_ERROR, str(e))
        )
