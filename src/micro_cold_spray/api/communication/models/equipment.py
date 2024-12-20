"""Equipment state models."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class EquipmentState(BaseModel):
    """Equipment state model."""

    gas: Dict[str, Any] = Field(
        default_factory=dict,
        description="Gas system state (valves, flows, pressures)"
    )
    vacuum: Dict[str, Any] = Field(
        default_factory=dict,
        description="Vacuum system state (pumps, valves, pressures)"
    )
    feeder: Dict[str, Any] = Field(
        default_factory=dict,
        description="Powder feeder state (frequency, running)"
    )
    nozzle: Dict[str, Any] = Field(
        default_factory=dict,
        description="Nozzle state (shutter, temperature)"
    )
    motion: Dict[str, Any] = Field(
        default_factory=dict,
        description="Motion system state (position, status)"
    )
    timestamp: Optional[float] = Field(
        None,
        description="State timestamp (seconds since epoch)"
    )
