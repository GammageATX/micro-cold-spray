"""Tag management endpoints."""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends

from ..models.tags import TagRequest, TagSubscription, TagUpdate
from ..service import CommunicationService
from ...base import get_service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/values")
async def get_tag_values(
    tags: List[str],
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get tag values."""
    try:
        values = await service.tag_cache.get_values(tags)
        return {"values": values}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/write")
async def write_tag_value(
    request: TagUpdate,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Write tag value."""
    try:
        await service.tag_cache.write_value(request.tag, request.value)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/subscribe")
async def subscribe_to_tags(
    request: TagSubscription,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Subscribe to tag updates."""
    try:
        await service.tag_cache.subscribe(request.tags, request.callback_url)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/unsubscribe")
async def unsubscribe_from_tags(
    request: TagSubscription,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Unsubscribe from tag updates."""
    try:
        await service.tag_cache.unsubscribe(request.tags, request.callback_url)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/mappings")
async def get_tag_mappings(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Get tag mappings."""
    try:
        mappings = await service.tag_mapping.get_mappings()
        return {"mappings": mappings}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/mappings")
async def update_tag_mapping(
    request: TagRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Update tag mapping."""
    try:
        await service.tag_mapping.update_mapping(request.tag_path, request.plc_tag)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
