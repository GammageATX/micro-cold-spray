"""Equipment state and request models."""

from typing import Literal
from pydantic import BaseModel, Field

from micro_cold_spray.api.communication.models.motion import Position, SystemStatus


class GasState(BaseModel):
    """Gas system state."""
    main_flow: float = Field(..., description="Main gas flow setpoint")
    main_flow_measured: float = Field(..., description="Main gas flow measured")
    feeder_flow: float = Field(..., description="Feeder gas flow setpoint")
    feeder_flow_measured: float = Field(..., description="Feeder gas flow measured")
    main_valve: bool = Field(..., description="Main gas valve state")
    feeder_valve: bool = Field(..., description="Feeder gas valve state")


class VacuumState(BaseModel):
    """Vacuum system state."""
    chamber_pressure: float = Field(..., description="Chamber pressure")
    gate_valve: bool = Field(..., description="Gate valve state")
    mech_pump: bool = Field(..., description="Mechanical pump state")
    booster_pump: bool = Field(..., description="Booster pump state")
    vent_valve: bool = Field(..., description="Vent valve state")


class FeederState(BaseModel):
    """Powder feeder state."""
    running: bool = Field(..., description="Whether feeder is running")
    frequency: float = Field(..., description="Feeder frequency in Hz")


class DeagglomeratorState(BaseModel):
    """Deagglomerator state."""
    duty_cycle: float = Field(..., description="Duty cycle percentage (higher = lower speed)")


class NozzleState(BaseModel):
    """Nozzle control state."""
    active_nozzle: Literal[1, 2] = Field(..., description="Active nozzle (1 or 2)")
    shutter_open: bool = Field(..., description="Shutter state")


class PressureState(BaseModel):
    """System pressure readings."""
    chamber: float = Field(..., description="Chamber pressure")
    feeder: float = Field(..., description="Feeder pressure")
    main_supply: float = Field(..., description="Main gas supply pressure")
    nozzle: float = Field(..., description="Nozzle pressure")
    regulator: float = Field(..., description="Regulator pressure")


class MotionState(BaseModel):
    """Motion system state."""
    position: Position = Field(..., description="Current position")
    status: SystemStatus = Field(..., description="Motion system status")


class HardwareState(BaseModel):
    """Hardware status."""
    motion_enabled: bool = Field(..., description="Motion system enabled")
    plc_connected: bool = Field(..., description="PLC connection status")
    position_valid: bool = Field(..., description="Position tracking valid")


class ProcessState(BaseModel):
    """Process status."""
    gas_flow_stable: bool = Field(..., description="Gas flow stability")
    powder_feed_active: bool = Field(..., description="Powder feeding active")
    process_ready: bool = Field(..., description="Process ready to start")


class SafetyState(BaseModel):
    """Safety system state."""
    emergency_stop: bool = Field(..., description="E-stop status")
    interlocks_ok: bool = Field(..., description="Interlock status")
    limits_ok: bool = Field(..., description="Limit switch status")


class EquipmentState(BaseModel):
    """Equipment state."""
    gas: GasState = Field(..., description="Gas system state")
    vacuum: VacuumState = Field(..., description="Vacuum system state")
    feeder: FeederState = Field(..., description="Powder feeder state")
    deagglomerator: DeagglomeratorState = Field(..., description="Deagglomerator state")
    nozzle: NozzleState = Field(..., description="Nozzle control state")
    pressure: PressureState = Field(..., description="System pressure readings")
    motion: MotionState = Field(..., description="Motion system state")
    hardware: HardwareState = Field(..., description="Hardware status")
    process: ProcessState = Field(..., description="Process status")
    safety: SafetyState = Field(..., description="Safety system state")


class SystemState(BaseModel):
    """Complete system state."""
    equipment: EquipmentState = Field(..., description="Equipment state")
    motion: MotionState = Field(..., description="Motion state")
    safety: dict = Field(..., description="Safety state")


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
    # Frequency is fixed at 500Hz, so removed from state updates
