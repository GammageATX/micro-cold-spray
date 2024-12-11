"""Equipment control request models."""

from pydantic import BaseModel, Field


class GasFlowRequest(BaseModel):
    """Request to set gas flow setpoint."""
    type: str = Field(
        description="Type of gas flow (main, carrier)",
        pattern="^(main|carrier)$"
    )
    value: float = Field(
        description="Flow setpoint in SLPM",
        ge=0.0,
        le=100.0
    )


class GasValveRequest(BaseModel):
    """Request to control gas valve."""
    valve: str = Field(
        description="Valve to control (main, carrier)",
        pattern="^(main|carrier)$"
    )
    state: bool = Field(
        description="Valve state (True=open, False=closed)"
    )


class PumpRequest(BaseModel):
    """Request to control vacuum pump."""
    state: bool = Field(
        description="Pump state (True=on, False=off)"
    )


class VacuumValveRequest(BaseModel):
    """Request to control vacuum valve."""
    valve: str = Field(
        description="Valve to control (chamber, bypass)",
        pattern="^(chamber|bypass)$"
    )
    state: bool = Field(
        description="Valve state (True=open, False=closed)"
    )


class FeederRequest(BaseModel):
    """Request to control powder feeder."""
    state: bool = Field(
        description="Feeder state (True=on, False=off)"
    )


class DeagglomeratorRequest(BaseModel):
    """Request to control deagglomerator."""
    state: bool = Field(
        description="Deagglomerator state (True=on, False=off)"
    )


class NozzleRequest(BaseModel):
    """Request to control nozzle heater."""
    state: bool = Field(
        description="Heater state (True=on, False=off)"
    )


class ShutterRequest(BaseModel):
    """Request to control nozzle shutter."""
    position: str = Field(
        description="Shutter position (open, closed, partial)",
        pattern="^(open|closed|partial)$"
    )
