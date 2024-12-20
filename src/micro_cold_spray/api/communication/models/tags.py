"""Tag data models."""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TagMetadata(BaseModel):
    """Tag metadata model."""

    name: str = Field(..., description="Tag name/path")
    description: str = Field("", description="Tag description")
    units: str = Field("", description="Tag units")
    min_value: Optional[float] = Field(None, description="Minimum allowed value")
    max_value: Optional[float] = Field(None, description="Maximum allowed value")
    is_mapped: bool = Field(False, description="Whether tag is mapped to hardware")


class TagValue(BaseModel):
    """Tag value model with metadata."""

    metadata: TagMetadata = Field(..., description="Tag metadata")
    value: Optional[Any] = Field(None, description="Current tag value")
    timestamp: datetime = Field(..., description="Last update timestamp")


class TagCacheResponse(BaseModel):
    """Tag cache response model."""

    tags: Dict[str, TagValue] = Field(..., description="Tag values by path")
    timestamp: datetime = Field(..., description="Response timestamp")
