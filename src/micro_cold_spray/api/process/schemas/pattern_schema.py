"""Pattern schema definition."""

from enum import Enum
from pydantic import BaseModel, Field


class PatternType(str, Enum):
    """Pattern types."""
    LINEAR = "linear"
    SERPENTINE = "serpentine"
    SPIRAL = "spiral"
    CUSTOM = "custom"


class PatternParams(BaseModel):
    """Pattern parameters."""
    width: float = Field(gt=0, le=500, description="Pattern width in mm")
    height: float = Field(gt=0, le=500, description="Pattern height in mm")
    z_height: float = Field(gt=0, le=100, description="Z height in mm")
    velocity: float = Field(gt=0, le=500, description="Motion velocity in mm/s")
    line_spacing: float = Field(gt=0.1, le=50, description="Line spacing in mm")
    direction: str = Field(pattern="^[xy]$", description="Primary motion direction")


class Pattern(BaseModel):
    """Pattern definition."""
    id: str = Field(description="Unique pattern identifier")
    name: str = Field(description="Pattern name")
    description: str = Field(description="Pattern description")
    type: PatternType = Field(description="Pattern type")
    params: PatternParams = Field(description="Pattern parameters")


class PatternData(BaseModel):
    """Pattern file structure."""
    pattern: Pattern
