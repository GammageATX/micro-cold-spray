"""Motion control request and response models."""

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


class MotionStatus(BaseModel):
    """Current motion system status."""
    x_position: float = Field(description="Current X position in mm")
    y_position: float = Field(description="Current Y position in mm")
    z_position: float = Field(description="Current Z position in mm")
    x_moving: bool = Field(description="X axis in motion")
    y_moving: bool = Field(description="Y axis in motion")
    z_moving: bool = Field(description="Z axis in motion")
    x_error: bool = Field(description="X axis error state")
    y_error: bool = Field(description="Y axis error state")
    z_error: bool = Field(description="Z axis error state")
