"""Motion models."""

from typing import Optional
from pydantic import BaseModel, Field


class Position(BaseModel):
    """Position model."""
    x: float = Field(..., description="X position")
    y: float = Field(..., description="Y position")
    z: float = Field(..., description="Z position")


class AxisStatus(BaseModel):
    """Axis status model."""
    position: float = Field(..., description="Current position")
    in_position: bool = Field(..., description="At target position")
    moving: bool = Field(..., description="Currently moving")
    error: bool = Field(..., description="Error state")
    homed: bool = Field(..., description="Homed state")


class SystemStatus(BaseModel):
    """Motion system status."""
    x_axis: AxisStatus = Field(..., description="X axis status")
    y_axis: AxisStatus = Field(..., description="Y axis status")
    z_axis: AxisStatus = Field(..., description="Z axis status")
    module_ready: bool = Field(..., description="Motion controller ready")


class JogRequest(BaseModel):
    """Jog motion request."""
    axis: str = Field(..., description="Axis to jog (x, y, z)")
    direction: int = Field(..., ge=-1, le=1, description="Jog direction (-1, 0, 1)")
    velocity: float = Field(..., gt=0, description="Jog velocity")


class MoveRequest(BaseModel):
    """Move request."""
    x: Optional[float] = Field(None, description="X target position")
    y: Optional[float] = Field(None, description="Y target position")
    z: Optional[float] = Field(None, description="Z target position")
    velocity: float = Field(..., gt=0, description="Move velocity")
