"""Parameter schema definition."""

from datetime import date
from pydantic import BaseModel, Field


class ProcessParameters(BaseModel):
    """Process parameters definition."""
    name: str = Field(description="Parameter set name")
    created: date = Field(description="Creation date")
    author: str = Field(description="Author name")
    description: str = Field(description="Parameter set description")
    nozzle: str = Field(description="Nozzle identifier")
    main_gas: float = Field(gt=0, le=100, description="Main gas flow rate (L/min)")
    feeder_gas: float = Field(gt=0, le=20, description="Feeder gas flow rate (L/min)")
    frequency: float = Field(gt=0, le=1000, description="Feeder frequency (Hz)")
    deagglomerator_speed: float = Field(gt=0, le=100, description="Deagglomerator speed (%)")


class ParameterData(BaseModel):
    """Parameter file structure."""
    process: ProcessParameters
