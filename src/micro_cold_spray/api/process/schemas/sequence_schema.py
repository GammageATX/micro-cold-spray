"""Sequence schema definition."""

from datetime import date
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class StepType(str, Enum):
    """Step types."""
    INITIALIZE = "initialize"
    PATTERN = "pattern"
    PARAMETER = "parameter"
    WAIT = "wait"
    CUSTOM = "custom"


class SequenceMetadata(BaseModel):
    """Sequence metadata."""
    name: str = Field(description="Sequence name")
    version: str = Field(description="Sequence version")
    created: date = Field(description="Creation date")
    author: str = Field(description="Author name")
    description: str = Field(description="Sequence description")


class SequenceStep(BaseModel):
    """Sequence step definition."""
    name: str = Field(description="Step name")
    step_type: StepType = Field(description="Step type")
    description: str = Field(description="Step description")
    pattern_id: Optional[str] = Field(None, description="Pattern identifier")
    parameters: Optional[Dict] = Field(None, description="Step parameters")
    wait_time: Optional[float] = Field(None, gt=0, description="Wait time in seconds")


class Sequence(BaseModel):
    """Sequence definition."""
    metadata: SequenceMetadata = Field(description="Sequence metadata")
    steps: List[SequenceStep] = Field(description="Sequence steps")


class SequenceData(BaseModel):
    """Sequence file structure."""
    sequence: Sequence
