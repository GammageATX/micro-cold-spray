"""Tag management endpoints."""

from fastapi import APIRouter, HTTPException, Depends

from .. import HardwareError
from ..router import get_plc_service, get_tag_cache
from ..services.plc_service import PLCTagService
from ..services.tag_cache import TagCacheService, ValidationError
from ..models.tags import (
    TagWriteRequest,
    TagResponse,
    TagCacheRequest,
    TagCacheResponse
)

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/{tag_path}")
async def get_tag(
    tag_path: str,
    plc_service: PLCTagService = Depends(get_plc_service),
    tag_cache: TagCacheService = Depends(get_tag_cache)
) -> TagResponse:
    """Get tag value with metadata."""
    try:
        # Get value from cache
        tag_value = tag_cache.get_tag_with_metadata(tag_path)
        
        # If mapped to hardware, get fresh value
        if tag_value.metadata.mapped:
            value = await plc_service.read_tag(tag_path)
            tag_cache.update_tag(tag_path, value)
            tag_value = tag_cache.get_tag_with_metadata(tag_path)
            
        return TagResponse(
            tag=tag_path,
            value=tag_value.value,
            metadata=tag_value.metadata,
            timestamp=tag_value.timestamp
        )
    except HardwareError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "device": e.device, "context": e.context}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tag_path}")
async def write_tag(
    tag_path: str,
    request: TagWriteRequest,
    plc_service: PLCTagService = Depends(get_plc_service),
    tag_cache: TagCacheService = Depends(get_tag_cache)
) -> TagResponse:
    """Write tag value."""
    try:
        # Get current metadata
        tag_value = tag_cache.get_tag_with_metadata(tag_path)
        
        # Validate write access
        if tag_value.metadata.access != "write":
            raise ValidationError(f"Tag {tag_path} is not writable")
            
        # Validate value against metadata
        tag_cache.validate_value(tag_path, request.value)
        
        # Write to hardware if mapped
        if tag_value.metadata.mapped:
            await plc_service.write_tag(tag_path, request.value)
            
        # Update cache
        tag_cache.update_tag(tag_path, request.value)
        tag_value = tag_cache.get_tag_with_metadata(tag_path)
        
        return TagResponse(
            tag=tag_path,
            value=tag_value.value,
            metadata=tag_value.metadata,
            timestamp=tag_value.timestamp
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": str(e)}
        )
    except HardwareError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": str(e), "device": e.device, "context": e.context}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/filter")
async def filter_tags(
    request: TagCacheRequest,
    tag_cache: TagCacheService = Depends(get_tag_cache)
) -> TagCacheResponse:
    """Get filtered tag values from cache."""
    try:
        return tag_cache.filter_tags(
            groups=request.groups,
            types=request.types,
            access=request.access
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": str(e)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
