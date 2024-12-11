"""Data models for data collection."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class CollectionSession:
    """Active data collection session info."""
    sequence_id: str
    start_time: datetime
    collection_params: Dict[str, Any]


@dataclass
class SprayEvent:
    """Data class representing a spray event."""
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
