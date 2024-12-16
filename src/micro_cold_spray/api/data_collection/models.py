"""Data models for data collection."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re


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
    """Data class representing a spray event."""
    model_config = ConfigDict(strict=True)
    
    id: Optional[int] = None
    sequence_id: str
    spray_index: int
    timestamp: datetime = Field(default_factory=datetime.now)
    x_pos: float
    y_pos: float
    z_pos: float
    pressure: float
    temperature: float
    flow_rate: float
    status: str
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def validate_timestamp(cls, v: Any) -> datetime:
        """Validate and convert timestamp to datetime."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError as e:
                raise ValueError(f"Invalid timestamp format: {e}")
        raise ValueError("Invalid timestamp type")
    
    @field_validator('pressure', 'temperature', 'flow_rate')
    @classmethod
    def validate_positive_values(cls, v: float, info: Any) -> float:
        """Validate that values are positive."""
        if v < 0:
            raise ValueError(f"{info.field_name} must be positive")
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
