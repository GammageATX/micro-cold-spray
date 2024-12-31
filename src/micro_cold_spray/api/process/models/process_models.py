"""Process API models."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, ConfigDict, Field


class BaseResponse(BaseModel):
    """Base response model."""
    model_config = ConfigDict(strict=True)
    
    message: str = Field(..., description="Response message")


class PatternType(str, Enum):
    """Pattern types."""
    LINEAR = "linear"           # Back and forth lines
    SERPENTINE = "serpentine"   # Continuous snake pattern
    SPIRAL = "spiral"           # Outward/inward spiral
    CUSTOM = "custom"           # Custom G-code pattern


class PatternParameters(BaseModel):
    """Pattern motion parameters."""
    model_config = ConfigDict(strict=True)
    
    width: float = Field(..., description="Pattern width in mm", ge=0, le=500)
    height: float = Field(..., description="Pattern height in mm", ge=0, le=500)
    z_height: float = Field(..., description="Z height in mm", ge=0, le=100)
    velocity: float = Field(..., description="Motion velocity in mm/s", ge=0, le=500)
    line_spacing: float = Field(..., description="Line spacing in mm", ge=0.1, le=50)
    direction: Optional[str] = Field("x", description="Primary motion axis (x/y)")
    start_point: Optional[Dict[str, float]] = Field(None, description="Starting coordinates")
    layers: Optional[int] = Field(1, description="Number of layers")
    layer_height: Optional[float] = Field(None, description="Z increment per layer")


class ProcessPattern(BaseModel):
    """Process pattern model."""
    model_config = ConfigDict(strict=True)
    
    id: str = Field(..., description="Pattern identifier")
    name: str = Field(..., description="Pattern name")
    description: str = Field(..., description="Pattern description")
    type: PatternType = Field(..., description="Pattern type")
    params: PatternParameters = Field(..., description="Pattern parameters")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ParameterSet(BaseModel):
    """Parameter set model."""
    model_config = ConfigDict(strict=True)
    
    id: str = Field(..., description="Parameter set identifier")
    name: str = Field(..., description="Parameter set name")
    description: str = Field(..., description="Parameter set description")
    nozzle: str = Field(..., description="Nozzle identifier")
    main_gas: float = Field(..., description="Main gas flow rate")
    feeder_gas: float = Field(..., description="Feeder gas flow rate")
    frequency: int = Field(..., description="Feeder frequency")
    deagglomerator_speed: int = Field(..., description="Deagglomerator speed")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class StepType(str, Enum):
    """Atomic hardware operations."""
    # Gas Flow Control
    SET_MAIN_FLOW = "set_main_flow"      # Set main gas MFC flow rate
    SET_FEEDER_FLOW = "set_feeder_flow"  # Set feeder gas MFC flow rate
    
    # Gas Valve Control
    SET_MAIN_VALVE = "set_main_valve"      # Main gas valve open/close
    SET_FEEDER_VALVE = "set_feeder_valve"  # Feeder gas valve open/close
    
    # Vacuum System
    SET_GATE_VALVE = "set_gate_valve"    # Vacuum gate valve open/close
    SET_VENT_VALVE = "set_vent_valve"    # Chamber vent valve open/close
    SET_MECH_PUMP = "set_mech_pump"      # Mechanical pump on/off
    SET_BOOSTER = "set_booster_pump"     # Booster pump on/off
    
    # Powder Feed System
    SET_FEEDER = "set_feeder"            # Set feeder frequency
    SET_DEAGG = "set_deagg"              # Set deagglomerator speed
    SELECT_FEEDER = "select_feeder"      # Switch active feeder (1/2)
    
    # Nozzle Control
    OPEN_SHUTTER = "open_shutter"        # Open nozzle shutter
    CLOSE_SHUTTER = "close_shutter"      # Close nozzle shutter
    SELECT_NOZZLE = "select_nozzle"      # Switch active nozzle (1/2)
    
    # Motion Control
    LOAD_PATTERN = "load_pattern"        # Load and execute pattern
    MOVE_TO = "move_to"                  # Move to absolute position
    HOME = "home"                        # Home all axes
    STOP_MOTION = "stop_motion"          # Emergency stop motion
    SET_SPEED = "set_speed"              # Set motion speed
    SET_ACCEL = "set_accel"              # Set acceleration
    ENABLE_AXES = "enable_axes"          # Enable motion axes
    DISABLE_AXES = "disable_axes"        # Disable motion axes


class ActionGroup(str, Enum):
    """Common operation sequences."""
    STARTUP = "startup"                  # Vacuum, valves, gas flows
    SHUTDOWN = "shutdown"                # Safe system shutdown
    MOVE_TO_TROUGH = "move_to_trough"    # Position for powder loading
    MOVE_TO_HOME = "move_to_home"        # Safe home position
    SPRAY_SETUP = "spray_setup"          # Pre-spray configuration
    SPRAY_CLEANUP = "spray_cleanup"      # Post-spray cleanup


class StepParameters(BaseModel):
    """Base parameters model."""
    model_config = ConfigDict(strict=True)


class FlowParameters(StepParameters):
    """Gas flow parameters."""
    flow_rate: float = Field(..., description="Flow rate in SLPM")


class ValveParameters(StepParameters):
    """Valve control parameters."""
    state: bool = Field(..., description="Valve state (open/close)")


class PumpParameters(StepParameters):
    """Pump control parameters."""
    state: bool = Field(..., description="Pump state (on/off)")


class FeederParameters(StepParameters):
    """Feeder control parameters."""
    frequency: int = Field(..., description="Frequency in Hz")


class DeaggParameters(StepParameters):
    """Deagglomerator control parameters."""
    speed: int = Field(..., description="Speed percentage")


class SelectionParameters(StepParameters):
    """Equipment selection parameters."""
    id: int = Field(..., description="Equipment ID (1/2)")


class MotionParameters(StepParameters):
    """Motion control parameters."""
    x: Optional[float] = Field(None, description="X position")
    y: Optional[float] = Field(None, description="Y position")
    z: Optional[float] = Field(None, description="Z position")
    speed: Optional[float] = Field(None, description="Motion speed")
    acceleration: Optional[float] = Field(None, description="Motion acceleration")


class SequenceStep(BaseModel):
    """Individual process step."""
    model_config = ConfigDict(strict=True)
    
    name: str = Field(..., description="Step name")
    description: Optional[str] = Field(None, description="Step description")
    step_type: StepType = Field(..., description="Atomic operation type")
    parameters: Optional[Union[
        FlowParameters,
        ValveParameters,
        PumpParameters,
        FeederParameters,
        DeaggParameters,
        SelectionParameters,
        MotionParameters,
        Dict[str, Any]
    ]] = Field(None, description="Step parameters")
    pattern_id: Optional[str] = Field(None, description="Associated pattern ID")
    parameter_id: Optional[str] = Field(None, description="Associated parameter set ID")


class Action(BaseModel):
    """Predefined sequence of steps."""
    model_config = ConfigDict(strict=True)
    
    group: ActionGroup = Field(..., description="Action group type")
    steps: List[SequenceStep] = Field(..., description="Steps in this action group")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Override parameters")


class SequenceMetadata(BaseModel):
    """Sequence metadata model."""
    model_config = ConfigDict(strict=True)
    
    name: str = Field(..., description="Sequence name")
    version: str = Field(..., description="Sequence version")
    created: datetime = Field(default_factory=datetime.now, description="Creation date")
    author: str = Field(..., description="Sequence author")
    description: str = Field(..., description="Sequence description")
    hardware_config: Optional[Dict[str, Any]] = Field(None, description="Hardware configuration")


class Sequence(BaseModel):
    """Sequence model."""
    model_config = ConfigDict(strict=True)
    
    id: str = Field(..., description="Sequence identifier")
    metadata: SequenceMetadata = Field(..., description="Sequence metadata")
    steps: List[SequenceStep] = Field(..., description="Sequence steps")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


# Response Models
class PatternResponse(BaseResponse):
    """Pattern operation response."""
    pattern: Optional[ProcessPattern] = Field(None, description="Process pattern")


class PatternListResponse(BaseResponse):
    """Pattern list response."""
    patterns: List[ProcessPattern] = Field(default_factory=list)


class ParameterSetResponse(BaseResponse):
    """Parameter set operation response."""
    parameter_set: Optional[ParameterSet] = Field(None, description="Parameter set")


class ParameterSetListResponse(BaseResponse):
    """Parameter set list response."""
    parameter_sets: List[ParameterSet] = Field(default_factory=list)


class SequenceResponse(BaseResponse):
    """Sequence operation response."""
    sequence: Optional[Dict[str, Any]] = Field(None, description="Sequence data")
    status: Optional[str] = Field(None, description="Execution status")
    step_number: Optional[int] = Field(None, description="Current step number")
    step_status: Optional[str] = Field(None, description="Current step status")
    error: Optional[str] = Field(None, description="Error message if any")


class SequenceListResponse(BaseResponse):
    """Sequence list response."""
    sequences: List[Dict[str, Any]] = Field(default_factory=list)


class SequenceStatus(str, Enum):
    """Sequence execution status."""
    IDLE = "idle"            # No sequence loaded
    READY = "ready"          # Sequence loaded, validated, hardware checked
    RUNNING = "running"      # Sequence is executing
    COMPLETED = "completed"  # Sequence finished successfully
    ERROR = "error"          # Sequence failed
