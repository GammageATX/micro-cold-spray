"""Tag endpoints."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, status, Depends
from pydantic import BaseModel, Field
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.communication_service import CommunicationService
from micro_cold_spray.api.communication.dependencies import get_communication_service


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


class WriteRequest(BaseModel):
    """Write request model."""
    tag_id: str = Field(..., description="Tag to write")
    value: Any = Field(..., description="Value to write")
    data_type: Optional[str] = Field(None, description="Optional data type override")


router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/read/{tag_id}")
async def read_tag(
    tag_id: str,
    service: CommunicationService = Depends(get_communication_service)
) -> TagValueResponse:
    """Read tag value.
    
    Args:
        tag_id: Tag identifier
        
    Returns:
        Tag value response
    """
    try:
        logger.debug(f"Reading tag {tag_id}")
        value = await service.tag_cache.read_tag(tag_id)
        
        return TagValueResponse(
            status="ok",
            tag_id=tag_id,
            value=value,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to read tag {tag_id}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to read tag {tag_id}"
        )


@router.get("/list")
async def list_tags(
    service: CommunicationService = Depends(get_communication_service)
) -> TagListResponse:
    """List available tags.
    
    Returns:
        List of available tags
    """
    try:
        logger.debug("Listing available tags")
        tags_list = await service.tag_cache.list_tags()
        
        return TagListResponse(
            status="ok",
            tags=tags_list,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to list tags: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to list tags"
        )


@router.post("/write")
async def write_tag(
    request: WriteRequest,
    service: CommunicationService = Depends(get_communication_service)
) -> TagResponse:
    """Write tag value.
    
    Args:
        request: Write request parameters
        
    Returns:
        Write response
    """
    try:
        logger.debug(f"Writing value {request.value} to tag {request.tag_id}")
        await service.tag_cache.write_tag(
            tag_id=request.tag_id,
            value=request.value,
            data_type=request.data_type
        )
        
        return TagResponse(
            status="ok",
            message=f"Wrote value {request.value} to tag {request.tag_id}",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to write tag {request.tag_id}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to write tag {request.tag_id}"
        )
