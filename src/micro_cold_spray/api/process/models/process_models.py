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
    direction: str = Field(..., pattern="^[xy]$", description="Primary motion axis")
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
    """Sequence step types."""
    INITIALIZE = "initialize"  # System initialization
    PATTERN = "pattern"       # Pattern execution
    PARAMETER = "parameter"   # Parameter adjustment
    WAIT = "wait"            # Time delay
    CUSTOM = "custom"        # Custom action


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
    """Sequence step model."""
    model_config = ConfigDict(strict=True)
    
    name: str = Field(..., description="Step name")
    step_type: StepType = Field(..., description="Step type")
    description: str = Field(..., description="Step description")
    pattern_id: Optional[str] = Field(None, description="Pattern ID for pattern steps")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Step parameters")
    wait_time: Optional[float] = Field(None, ge=0, description="Wait time in seconds")


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


class ExecutionStatus(str, Enum):
    """Sequence execution status."""
    IDLE = "idle"            # No sequence loaded
    READY = "ready"          # Sequence loaded and validated
    RUNNING = "running"      # Sequence is executing
    PAUSED = "paused"        # Sequence execution paused
    COMPLETED = "completed"  # Sequence finished successfully
    ERROR = "error"          # Sequence failed
    ABORTED = "aborted"      # Sequence manually stopped


class ActionStatus(str, Enum):
    """Action execution status."""
    IDLE = "idle"            # No action running
    RUNNING = "running"      # Action in progress
    COMPLETED = "completed"  # Action completed successfully
    ERROR = "error"          # Action failed
    ABORTED = "aborted"      # Action manually stopped


class NozzleResponse(BaseResponse):
    """Nozzle operation response."""
    nozzle: Optional[Dict[str, Any]] = Field(None, description="Nozzle data")


class NozzleListResponse(BaseResponse):
    """Nozzle list response."""
    nozzles: List[Dict[str, Any]] = Field(default_factory=list)


class PowderResponse(BaseResponse):
    """Powder operation response."""
    powder: Optional[Dict[str, Any]] = Field(None, description="Powder data")


class PowderListResponse(BaseResponse):
    """Powder list response."""
    powders: List[Dict[str, Any]] = Field(default_factory=list)
