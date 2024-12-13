"""Motion control request and response models."""

from typing import Dict
from pydantic import BaseModel, Field


class SingleAxisMoveRequest(BaseModel):
    """Request for single axis move."""
    axis: str = Field(
        description="Axis to move (x, y, z)",
        pattern="^[xyz]$"
    )
    position: float = Field(
        description="Target position in mm",
        ge=-1000.0,
        le=1000.0
    )
    velocity: float = Field(
        description="Move velocity in mm/s",
        ge=0.0,
        le=100.0
    )


class CoordinatedMoveRequest(BaseModel):
    """Request for coordinated XY move."""
    x_position: float = Field(
        description="X target position in mm",
        ge=-1000.0,
        le=1000.0
    )
    y_position: float = Field(
        description="Y target position in mm",
        ge=-1000.0,
        le=1000.0
    )
    velocity: float = Field(
        description="Move velocity in mm/s",
        ge=0.0,
        le=100.0
    )


class AxisStatus(BaseModel):
    """Status for a single axis."""
    position: float = Field(description="Current position in mm")
    moving: bool = Field(description="Axis in motion")
    complete: bool = Field(description="Move complete")
    status: int = Field(description="Detailed axis status")


class MotionStatus(BaseModel):
    """Current motion system status."""
    position: Dict[str, float] = Field(description="Current axis positions")
    moving: Dict[str, bool] = Field(description="Axis motion states")
    complete: Dict[str, bool] = Field(description="Axis completion states")
    status: Dict[str, int] = Field(description="Detailed axis status values")
