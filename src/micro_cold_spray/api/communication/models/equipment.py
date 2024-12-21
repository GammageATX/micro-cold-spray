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


class GasFlowRequest(BaseModel):
    """Gas flow control request."""
    flow_rate: float = Field(..., description="Flow rate setpoint")
    gas_type: str = Field(..., description="Type of gas to control")


class GasValveRequest(BaseModel):
    """Gas valve control request."""
    valve_id: str = Field(..., description="Valve identifier")
    state: bool = Field(..., description="Desired valve state (open/closed)")


class VacuumPumpRequest(BaseModel):
    """Vacuum pump control request."""
    pump_id: str = Field(..., description="Pump identifier")
    state: bool = Field(..., description="Desired pump state (on/off)")


class GateValveRequest(BaseModel):
    """Gate valve control request."""
    valve_id: str = Field(..., description="Valve identifier")
    state: bool = Field(..., description="Desired valve state (open/closed)")


class ShutterRequest(BaseModel):
    """Nozzle shutter control request."""
    state: bool = Field(..., description="Desired shutter state (open/closed)")


class FeederRequest(BaseModel):
    """Powder feeder control request."""
    frequency: Optional[float] = Field(None, description="Feeder frequency setpoint")
    state: bool = Field(..., description="Desired feeder state (on/off)")
