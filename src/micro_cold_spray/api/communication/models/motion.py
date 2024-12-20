"""Motion control models."""

from typing import Optional
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
