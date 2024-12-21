"""Motion control models."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class Position(BaseModel):
    """Position model with XYZ coordinates."""

    x: Optional[float] = Field(None, description="X position in mm")
    y: Optional[float] = Field(None, description="Y position in mm")
    z: Optional[float] = Field(None, description="Z position in mm")


class Velocity(BaseModel):
    """Velocity model with XYZ components."""

    x: Optional[float] = Field(None, description="X velocity in mm/s")
    y: Optional[float] = Field(None, description="Y velocity in mm/s")
    z: Optional[float] = Field(None, description="Z velocity in mm/s")
    path: Optional[float] = Field(None, description="Path velocity in mm/s")


class SingleAxisMoveRequest(BaseModel):
    """Single axis move request."""
    axis_id: str = Field(..., description="Axis identifier")
    position: float = Field(..., description="Target position")
    velocity: Optional[float] = Field(None, description="Optional velocity override")


class CoordinatedMoveRequest(BaseModel):
    """Coordinated multi-axis move request."""
    position: Position = Field(..., description="Target position")
    velocity: Optional[Velocity] = Field(None, description="Optional velocity override")


class MotionStatus(BaseModel):
    """Motion system status."""
    position: Position = Field(..., description="Current position")
    velocity: Velocity = Field(..., description="Current velocity")
    state: Dict[str, Any] = Field(..., description="Motion system state")
    error: Optional[str] = Field(None, description="Error message if any")
