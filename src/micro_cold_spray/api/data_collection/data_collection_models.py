"""Data models for data collection."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re
import math


class CollectionSession(BaseModel):
    """Active data collection session info."""
    model_config = ConfigDict(strict=True)
    
    sequence_id: str
    start_time: datetime
    collection_params: Dict[str, Any]
    
    def __str__(self) -> str:
        """Return string representation."""
        return (
            f"CollectionSession(sequence_id='{self.sequence_id}', "
            f"start_time={self.start_time.isoformat()}, "
            f"collection_params={self.collection_params})"
        )


class SprayEvent(BaseModel):
    """Model for spray event data."""
    
    id: Optional[int] = None
    sequence_id: str = Field(..., description="ID of sequence this event belongs to")
    spray_index: int = Field(..., description="Index of this event in the sequence")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this event occurred")
    x_pos: float = Field(..., description="X position", ge=-1e308, le=1e308)
    y_pos: float = Field(..., description="Y position", ge=-1e308, le=1e308)
    z_pos: float = Field(..., description="Z position", ge=-1e308, le=1e308)
    pressure: float = Field(..., description="Gas pressure", ge=0, le=1e308)
    temperature: float = Field(..., description="Gas temperature", ge=0, le=1e308)
    flow_rate: float = Field(..., description="Powder flow rate", ge=0, le=1e308)
    status: str = Field(default="active", description="Event status")
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def validate_timestamp(cls, v: Any) -> datetime:
        """Validate and convert timestamp to datetime."""
        if isinstance(v, datetime):
            if not v.tzinfo:
                v = v.replace(tzinfo=timezone.utc)
            return v
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError as e:
                raise ValueError(f"Invalid timestamp format: {e}")
        raise ValueError("Invalid timestamp type")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp_not_future(cls, v: datetime) -> datetime:
        """Validate timestamp is not in the future."""
        now = datetime.now(timezone.utc)
        if v > now:
            raise ValueError("Timestamp cannot be in the future")
        return v
    
    @field_validator('x_pos', 'y_pos', 'z_pos')
    @classmethod
    def validate_position(cls, v: float, info: Any) -> float:
        """Validate position values are finite."""
        if not math.isfinite(v):
            raise ValueError(f"{info.field_name} must be a finite number")
        return v
    
    @field_validator('sequence_id')
    @classmethod
    def validate_sequence_id(cls, v: str) -> str:
        """Validate sequence ID format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Sequence ID must contain only alphanumeric characters, underscores, and hyphens")
        return v
    
    def __str__(self) -> str:
        """Return string representation."""
        return (
            f"SprayEvent(sequence_id='{self.sequence_id}', "
            f"spray_index={self.spray_index}, "
            f"timestamp={self.timestamp.isoformat()}, "
            f"pos=({self.x_pos}, {self.y_pos}, {self.z_pos}), "
            f"pressure={self.pressure}, temp={self.temperature}, "
            f"flow={self.flow_rate}, status='{self.status}')"
        )
