"""Nozzle schema definition."""

from enum import Enum
from pydantic import BaseModel, Field


class NozzleType(str, Enum):
    """Nozzle types."""
    CONVERGENT_DIVERGENT = "convergent-divergent"
    CONVERGENT = "convergent"


class Nozzle(BaseModel):
    """Nozzle definition."""
    name: str = Field(description="Nozzle name")
    type: NozzleType = Field(description="Nozzle type")
    throat_diameter: float = Field(gt=0.1, le=10.0, description="Throat diameter (mm)")
    exit_diameter: float = Field(gt=0.1, le=10.0, description="Exit diameter (mm)")
    length: float = Field(gt=10, le=500, description="Nozzle length (mm)")


class NozzleData(BaseModel):
    """Nozzle file structure."""
    nozzle: Nozzle
