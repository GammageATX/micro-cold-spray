"""Nozzle schema definition."""

from enum import Enum
from pydantic import BaseModel, Field


class NozzleType(str, Enum):
    """Nozzle types."""
    CONVERGENT_DIVERGENT = "convergent-divergent"
    CONVERGENT = "convergent"
    VENTED = "vented"
    FLAT_PLATE = "flat-plate"
    DE_LAVAL = "de laval"


class Nozzle(BaseModel):
    """Nozzle definition."""
    name: str = Field(description="Nozzle name")
    type: NozzleType = Field(description="Nozzle type")


class NozzleData(BaseModel):
    """Nozzle file structure."""
    nozzle: Nozzle
