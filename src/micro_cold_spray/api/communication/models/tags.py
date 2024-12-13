"""Tag management models."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


class TagMetadata(BaseModel):
    """
    Metadata describing a tag's properties and constraints.
    
    All values and ranges are in engineering units (e.g., SLPM, torr, mm).
    """
    type: str = Field(
        description="Data type of the tag (float, integer, bool, string)"
    )
    access: str = Field(
        description="Access level: 'read' or 'read/write'"
    )
    description: str = Field(
        description="Human-readable description of the tag"
    )
    unit: Optional[str] = Field(
        None,
        description="Engineering unit (e.g., SLPM, torr, mm)"
    )
    range: Optional[List[float]] = Field(
        None,
        description="Valid range [min, max] in engineering units"
    )
    states: Optional[Dict[str, str]] = Field(
        None,
        description="Valid states for enumerated values"
    )
    options: Optional[List[str]] = Field(
        None,
        description="Valid options for choice fields"
    )
    mapped: bool = Field(
        False,
        description="Whether this tag is mapped to hardware"
    )
    writable: bool = Field(
        False,
        description="Whether this tag can be written to"
    )
    group: str = Field(
        description="Top-level group this tag belongs to"
    )


class TagValue(BaseModel):
    """
    A tag value with its metadata and timestamp.
    
    Values are always in engineering units or human-readable form.
    The API handles all conversions to/from hardware values.
    """
    value: Any = Field(
        description="Tag value in engineering units or human-readable form"
    )
    metadata: TagMetadata = Field(
        description="Tag metadata describing properties and constraints"
    )
    timestamp: datetime = Field(
        description="When this value was last updated"
    )


class TagRequest(BaseModel):
    """Request to read a single tag value."""
    tag_path: str = Field(
        description="Full path to the tag (e.g., 'gas_control.main_flow.setpoint')"
    )


class TagWriteRequest(BaseModel):
    """
    Request to write a tag value.
    
    The value should be in engineering units or human-readable form.
    Examples:
    - Flow setpoint: 75.0 (SLPM)
    - Deagglomerator speed: "medium"
    - Valve state: true
    """
    value: Any = Field(
        description="Value in engineering units or human-readable form"
    )


class TagResponse(BaseModel):
    """Response containing a tag's value and metadata."""
    tag: str = Field(
        description="Full path of the tag"
    )
    value: Any = Field(
        description="Current value in engineering units or human-readable form"
    )
    metadata: TagMetadata = Field(
        description="Tag metadata describing properties and constraints"
    )
    timestamp: datetime = Field(
        description="When this value was last updated"
    )


class TagCacheRequest(BaseModel):
    """
    Request to get filtered tag values from the cache.
    
    All filters are optional. If a filter is not provided,
    no filtering is done on that property.
    """
    groups: Optional[Set[str]] = Field(
        None,
        description="Only return tags from these groups"
    )
    types: Optional[Set[str]] = Field(
        None,
        description="Only return tags of these types (float, bool, etc)"
    )
    access: Optional[Set[str]] = Field(
        None,
        description="Only return tags with this access (read, read/write)"
    )


class TagCacheResponse(BaseModel):
    """Response containing filtered tag values from the cache."""
    tags: Dict[str, TagValue] = Field(
        description="Map of tag paths to their current values and metadata"
    )
    timestamp: datetime = Field(
        description="When this cache snapshot was taken"
    )
    groups: Set[str] = Field(
        description="Groups present in the filtered results"
    )


class TagUpdate(BaseModel):
    """Request to update a tag value."""
    tag: str = Field(
        description="Full path to the tag (e.g., 'gas_control.main_flow.setpoint')"
    )
    value: Any = Field(
        description="New value in engineering units or human-readable form"
    )


class TagSubscription(BaseModel):
    """Request to subscribe to tag updates."""
    tags: List[str] = Field(
        description="List of tag paths to subscribe to"
    )
    callback_url: str = Field(
        description="URL to receive tag update notifications"
    )
