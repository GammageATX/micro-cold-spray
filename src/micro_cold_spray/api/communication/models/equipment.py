"""Equipment state and request models."""

from typing import Literal
from pydantic import BaseModel, Field


class GasState(BaseModel):
    """Gas system state."""
    main_flow: float = Field(..., description="Main gas flow rate")
    feeder_flow: float = Field(..., description="Feeder gas flow rate")
    main_valve: bool = Field(..., description="Main gas valve state")
    feeder_valve: bool = Field(..., description="Feeder gas valve state")


class VacuumState(BaseModel):
    """Vacuum system state."""
    chamber_pressure: float = Field(..., description="Chamber pressure")
    gate_valve: bool = Field(..., description="Gate valve state")
    mech_pump: bool = Field(..., description="Mechanical pump state")
    booster_pump: bool = Field(..., description="Booster pump state")


class FeederState(BaseModel):
    """Powder feeder state."""
    running: bool = Field(..., description="Whether feeder is running")
    frequency: float = Field(..., description="Feeder frequency in Hz")


class NozzleState(BaseModel):
    """Nozzle control state."""
    active_nozzle: Literal[1, 2] = Field(..., description="Active nozzle (1 or 2)")
    shutter_open: bool = Field(..., description="Shutter state")
    pressure: float = Field(..., description="Nozzle pressure")


class EquipmentState(BaseModel):
    """Overall equipment state."""
    gas: GasState = Field(..., description="Gas system state")
    vacuum: VacuumState = Field(..., description="Vacuum system state")
    feeder1: FeederState = Field(..., description="Feeder 1 state")
    feeder2: FeederState = Field(..., description="Feeder 2 state")
    nozzle: NozzleState = Field(..., description="Nozzle state")


# Request Models
class GasFlowRequest(BaseModel):
    """Gas flow control request."""
    flow_rate: float = Field(..., ge=0, description="Flow rate setpoint")


class GasValveRequest(BaseModel):
    """Gas valve control request."""
    open: bool = Field(..., description="Whether to open valve")


class VacuumPumpRequest(BaseModel):
    """Vacuum pump control request."""
    start: bool = Field(..., description="Whether to start pump")


class GateValveRequest(BaseModel):
    """Gate valve control request."""
    position: Literal["open", "partial", "closed"] = Field(..., description="Valve position")


class ShutterRequest(BaseModel):
    """Shutter control request."""
    open: bool = Field(..., description="Whether to open shutter")


class FeederRequest(BaseModel):
    """Feeder control request."""
    frequency: float = Field(..., ge=0, le=1000, description="Operating frequency in Hz")


class DeagglomeratorRequest(BaseModel):
    """Deagglomerator control request."""
    duty_cycle: float = Field(..., ge=20, le=35, description="Duty cycle percentage")
    frequency: Literal[500] = Field(500, description="Operating frequency in Hz (fixed at 500Hz)")
