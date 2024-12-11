"""Tag management endpoints."""

from fastapi import APIRouter, HTTPException, Depends

from ..exceptions import HardwareError
from ..services import TagCacheService, TagMappingService
from ..models.tags import (
    TagWriteRequest,
    TagResponse,
    TagCacheRequest,
    TagCacheResponse,
    TagError
)

router = APIRouter(prefix="/tags", tags=["tags"])

# Service instances
_tag_cache: TagCacheService | None = None
_tag_mapping: TagMappingService | None = None


def init_router(
    tag_cache: TagCacheService,
    tag_mapping: TagMappingService
) -> None:
    """Initialize router with service instances."""
    global _tag_cache, _tag_mapping
    _tag_cache = tag_cache
    _tag_mapping = tag_mapping


def get_tag_cache() -> TagCacheService:
    """Get tag cache instance."""
    if not _tag_cache:
        raise RuntimeError("Tag cache not initialized")
    return _tag_cache


def get_tag_mapping() -> TagMappingService:
    """Get tag mapping instance."""
    if not _tag_mapping:
        raise RuntimeError("Tag mapping not initialized")
    return _tag_mapping


@router.get("/{tag_path}", response_model=TagResponse)
async def get_tag(
    tag_path: str,
    tag_cache: TagCacheService = Depends(get_tag_cache),
    tag_mapping: TagMappingService = Depends(get_tag_mapping)
) -> TagResponse:
    """Get tag value with metadata.
    
    Args:
        tag_path: Full path to the tag
        
    Returns:
        Tag value with metadata
        
    Raises:
        HTTPException: If tag read fails
    """
    try:
        # Get value and metadata from cache
        tag_value = await tag_cache.get_tag(tag_path)
        
        # If mapped to hardware, get fresh value
        if tag_value.metadata.mapped:
            value = await tag_mapping.read_tag(tag_path)
            await tag_cache.update_tag(tag_path, value)
            tag_value = await tag_cache.get_tag(tag_path)
            
        return TagResponse(
            tag=tag_path,
            value=tag_value.value,
            metadata=tag_value.metadata,
            timestamp=tag_value.timestamp
        )
    except HardwareError as e:
        raise HTTPException(
            status_code=400,
            detail=TagError(
                message=str(e),
                device=e.device,
                context=e.context
            ).dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=TagError(message=str(e)).dict()
        )


@router.post("/{tag_path}", response_model=TagResponse)
async def write_tag(
    tag_path: str,
    request: TagWriteRequest,
    tag_cache: TagCacheService = Depends(get_tag_cache),
    tag_mapping: TagMappingService = Depends(get_tag_mapping)
) -> TagResponse:
    """Write tag value.
    
    Args:
        tag_path: Full path to the tag
        request: Write request with value
        
    Returns:
        Updated tag value with metadata
        
    Raises:
        HTTPException: If tag write fails
    """
    try:
        # Get current metadata
        tag_value = await tag_cache.get_tag(tag_path)
        
        # Validate write access
        if not tag_value.metadata.writable:
            raise ValueError(f"Tag {tag_path} is not writable")
            
        # Validate value against metadata
        await tag_cache.validate_value(tag_path, request.value)
        
        # Write to hardware if mapped
        if tag_value.metadata.mapped:
            await tag_mapping.write_tag(tag_path, request.value)
            
        # Update cache
        await tag_cache.update_tag(tag_path, request.value)
        tag_value = await tag_cache.get_tag(tag_path)
        
        return TagResponse(
            tag=tag_path,
            value=tag_value.value,
            metadata=tag_value.metadata,
            timestamp=tag_value.timestamp
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=TagError(message=str(e)).dict()
        )
    except HardwareError as e:
        raise HTTPException(
            status_code=400,
            detail=TagError(
                message=str(e),
                device=e.device,
                context=e.context
            ).dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=TagError(message=str(e)).dict()
        )


@router.post("/cache/filter", response_model=TagCacheResponse)
async def filter_tags(
    request: TagCacheRequest,
    tag_cache: TagCacheService = Depends(get_tag_cache)
) -> TagCacheResponse:
    """Get filtered tag values from cache.
    
    Args:
        request: Filter criteria
        
    Returns:
        Filtered tag values with metadata
        
    Raises:
        HTTPException: If filtering fails
    """
    try:
        return await tag_cache.filter_tags(
            groups=request.groups,
            types=request.types,
            access=request.access
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=TagError(message=str(e)).dict()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=TagError(message=str(e)).dict()
        )
