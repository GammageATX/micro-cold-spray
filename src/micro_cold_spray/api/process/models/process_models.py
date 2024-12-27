"""Process API models."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
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
    parameters: Dict[str, Any] = Field(..., description="Pattern parameters")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class ParameterSet(BaseModel):
    """Parameter set model."""
    model_config = ConfigDict(strict=True)
    
    id: str = Field(..., description="Parameter set identifier")
    name: str = Field(..., description="Parameter set name")
    description: str = Field(..., description="Parameter set description")
    parameters: Dict[str, Any] = Field(..., description="Parameter values")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class SequenceStep(BaseModel):
    """Sequence step model."""
    model_config = ConfigDict(strict=True)
    
    id: str = Field(..., description="Step identifier")
    name: str = Field(..., description="Step name")
    description: str = Field(..., description="Step description")
    pattern_id: str = Field(..., description="Pattern identifier")
    parameter_set_id: str = Field(..., description="Parameter set identifier")
    order: int = Field(..., description="Step order")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class SequenceMetadata(BaseModel):
    """Sequence metadata model."""
    model_config = ConfigDict(strict=True)
    
    id: str = Field(..., description="Sequence identifier")
    name: str = Field(..., description="Sequence name")
    description: str = Field(..., description="Sequence description")
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
    sequence: Optional[SequenceMetadata] = Field(None, description="Sequence metadata")
    status: Optional[ExecutionStatus] = Field(None, description="Sequence execution status")


class SequenceListResponse(BaseResponse):
    """Sequence list response."""
    sequences: List[SequenceMetadata] = Field(default_factory=list, description="List of sequences")
