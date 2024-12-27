"""Process API models."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, ConfigDict, Field


class BaseResponse(BaseModel):
    """Base response model."""
    model_config = ConfigDict(strict=True)
    
    message: str = Field(..., description="Response message")


class ExecutionStatus(str, Enum):
    """Process execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class ActionStatus(str, Enum):
    """Action execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


class ProcessPattern(BaseModel):
    """Process pattern model."""
    model_config = ConfigDict(strict=True)
    
    id: str = Field(..., description="Pattern identifier")
    name: str = Field(..., description="Pattern name")
    description: str = Field(..., description="Pattern description")
    type: str = Field(..., description="Pattern type (linear, serpentine, spiral, custom)")
    params: Dict[str, Any] = Field(..., description="Pattern parameters")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


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
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class ActionGroup(BaseModel):
    """Action group model."""
    model_config = ConfigDict(strict=True)
    
    action_group: str = Field(..., description="Action group name")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Action group parameters")


class Action(BaseModel):
    """Action model."""
    model_config = ConfigDict(strict=True)
    
    action_group: str = Field(..., description="Action group name")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Action parameters")


class SequenceStep(BaseModel):
    """Sequence step model."""
    model_config = ConfigDict(strict=True)
    
    name: str = Field(..., description="Step name")
    description: Optional[str] = Field(None, description="Step description")
    action_group: Optional[str] = Field(None, description="Action group name")
    actions: Optional[List[Action]] = Field(None, description="List of actions")


class SequenceMetadata(BaseModel):
    """Sequence metadata model."""
    model_config = ConfigDict(strict=True)
    
    name: str = Field(..., description="Sequence name")
    version: str = Field(..., description="Sequence version")
    created: str = Field(..., description="Creation date")
    author: str = Field(..., description="Sequence author")
    description: str = Field(..., description="Sequence description")


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
    patterns: List[ProcessPattern] = Field(default_factory=list, description="List of patterns")


class ParameterSetResponse(BaseResponse):
    """Parameter set operation response."""
    parameter_set: Optional[ParameterSet] = Field(None, description="Parameter set")


class ParameterSetListResponse(BaseResponse):
    """Parameter set list response."""
    parameter_sets: List[ParameterSet] = Field(default_factory=list, description="List of parameter sets")


class SequenceResponse(BaseResponse):
    """Sequence operation response."""
    sequence: Optional[Sequence] = Field(None, description="Sequence")
    status: Optional[ExecutionStatus] = Field(None, description="Sequence execution status")


class SequenceListResponse(BaseResponse):
    """Sequence list response."""
    sequences: List[Sequence] = Field(default_factory=list, description="List of sequences")
