"""Equipment control request models."""

from pydantic import BaseModel, Field


class GasFlowRequest(BaseModel):
    """Request to set gas flow setpoint."""
    flow_type: str = Field(
        description="Type of gas flow (main, feeder)",
        pattern="^(main|feeder)$"
    )
    value: float = Field(
        description="Flow setpoint in SLPM",
        ge=0.0,
        le=100.0
    )


class GasValveRequest(BaseModel):
    """Request to control gas valve."""
    valve: str = Field(
        description="Valve to control (main, feeder)",
        pattern="^(main|feeder)$"
    )
    state: bool = Field(
        description="Valve state (True=open, False=closed)"
    )


class VacuumPumpRequest(BaseModel):
    """Request to control vacuum pump."""
    pump: str = Field(
        description="Pump to control (mechanical, booster)",
        pattern="^(mechanical|booster)$"
    )
    state: bool = Field(
        description="Pump state (True=start, False=stop)"
    )


class ShutterRequest(BaseModel):
    """Request to control nozzle shutter."""
    state: bool = Field(
        description="Shutter state (True=open, False=closed)"
    )


class GateValveRequest(BaseModel):
    """Request to control vacuum gate valve."""
    position: str = Field(
        description="Gate valve position (open, partial, closed)",
        pattern="^(open|partial|closed)$"
    )


class FeederRequest(BaseModel):
    """Request to control powder feeder."""
    frequency: float = Field(
        description="Feeder frequency in Hz",
        ge=200.0,
        le=1200.0
    )
    start: bool = Field(
        description="Start/stop feeder (True=start, False=stop)"
    )
