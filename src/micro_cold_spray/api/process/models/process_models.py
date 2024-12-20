"""Process API models."""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Process execution status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"
    ERROR = "error"


class ActionStatus(str, Enum):
    """Action execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessPattern(BaseModel):
    """Process pattern model."""
    id: str = Field(..., description="Pattern ID")
    name: str = Field(..., description="Pattern name")
    description: Optional[str] = Field(None, description="Pattern description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Pattern parameters")


class ParameterSet(BaseModel):
    """Parameter set model."""
    id: str = Field(..., description="Parameter set ID")
    name: str = Field(..., description="Parameter set name")
    description: Optional[str] = Field(None, description="Parameter set description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameter values")


class SequenceStep(BaseModel):
    """Sequence step model."""
    pattern_id: str = Field(..., description="Pattern ID")
    parameter_id: str = Field(..., description="Parameter set ID")
    description: Optional[str] = Field(None, description="Step description")


class SequenceMetadata(BaseModel):
    """Sequence metadata model."""
    id: str = Field(..., description="Sequence ID")
    name: str = Field(..., description="Sequence name")
    description: Optional[str] = Field(None, description="Sequence description")
    steps: List[SequenceStep] = Field(default_factory=list, description="Sequence steps")
