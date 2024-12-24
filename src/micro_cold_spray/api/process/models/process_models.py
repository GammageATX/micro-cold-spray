"""Process API models."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


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
    id: str = Field(..., description="Pattern identifier")
    name: str = Field(..., description="Pattern name")
    description: str = Field(..., description="Pattern description")
    parameters: Dict[str, Any] = Field(..., description="Pattern parameters")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class ParameterSet(BaseModel):
    """Parameter set model."""
    id: str = Field(..., description="Parameter set identifier")
    name: str = Field(..., description="Parameter set name")
    description: str = Field(..., description="Parameter set description")
    parameters: Dict[str, Any] = Field(..., description="Parameter values")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class SequenceStep(BaseModel):
    """Sequence step model."""
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
    id: str = Field(..., description="Sequence identifier")
    name: str = Field(..., description="Sequence name")
    description: str = Field(..., description="Sequence description")
    steps: List[SequenceStep] = Field(..., description="Sequence steps")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status (ok or error)")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    running: bool = Field(..., description="Whether service is running")
    uptime: float = Field(..., description="Service uptime in seconds")
    sub_services: Dict[str, Any] = Field(..., description="Sub-service health status")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
