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
    """Model for spray event data."""
    
    spray_index: int = Field(..., description="Index of this event in the sequence")
    sequence_id: str = Field(..., description="ID of sequence this event belongs to")
    material_type: str = Field(..., description="Type of powder material")
    pattern_name: str = Field(..., description="Name of spray pattern")
    operator: str = Field(..., description="Name of operator")
    start_time: datetime = Field(..., description="When spray started")
    end_time: Optional[datetime] = Field(None, description="When spray ended")
    powder_size: str = Field(..., description="Powder particle size range")
    powder_lot: str = Field(..., description="Powder lot number")
    manufacturer: str = Field(..., description="Powder manufacturer")
    nozzle_type: str = Field(..., description="Type of spray nozzle")
    chamber_pressure_start: float = Field(..., ge=0, description="Initial chamber pressure (bar)")
    chamber_pressure_end: float = Field(..., ge=0, description="Final chamber pressure (bar)")
    nozzle_pressure_start: float = Field(..., ge=0, description="Initial nozzle pressure (bar)")
    nozzle_pressure_end: float = Field(..., ge=0, description="Final nozzle pressure (bar)")
    main_flow: float = Field(..., ge=0, description="Main gas flow rate (slpm)")
    feeder_flow: float = Field(..., ge=0, description="Powder feeder flow rate (rpm)")
    feeder_frequency: float = Field(..., ge=0, description="Powder feeder frequency (Hz)")
    pattern_type: str = Field(..., description="Type of spray pattern")
    completed: bool = Field(..., description="Whether spray completed successfully")
    error: Optional[str] = Field(None, description="Error message if spray failed")
    
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
            f"start_time={self.start_time.isoformat()}, "
            f"pattern='{self.pattern_name}', "
            f"completed={self.completed})"
        )
