"""Data models for data collection."""

from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, ConfigDict


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
    
    sequence_id: str
    spray_index: int
    timestamp: datetime
    x_pos: float
    y_pos: float
    z_pos: float
    pressure: float
    temperature: float
    flow_rate: float
    status: str
    
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
