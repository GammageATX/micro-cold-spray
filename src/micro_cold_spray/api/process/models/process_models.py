"""Process API models."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# Enums
class NozzleType(str, Enum):
    """Nozzle types."""
    CONVERGENT_DIVERGENT = "convergent-divergent"
    CONVERGENT = "convergent"
    VENTED = "vented"
    FLAT_PLATE = "flat-plate"
    DE_LAVAL = "de laval"


# Base Models
class SizeRange(BaseModel):
    """Powder size range."""
    min: float = Field(gt=0, description="Minimum particle size (μm)")
    max: float = Field(gt=0, description="Maximum particle size (μm)")


class Nozzle(BaseModel):
    """Nozzle definition."""
    name: str
    type: NozzleType


class Powder(BaseModel):
    """Powder definition."""
    name: str
    type: str
    size: str
    manufacturer: str
    lot: str


class Pattern(BaseModel):
    """Pattern definition."""
    id: str
    name: str
    description: str
    type: str
    params: Dict[str, Any]


class Parameter(BaseModel):
    """Parameter set definition."""
    id: str
    name: str
    description: str
    nozzle_id: str
    powder_id: str
    gas_params: Dict[str, float]
    feeder_params: Dict[str, float]
    deagg_params: Dict[str, float]


class Sequence(BaseModel):
    """Sequence definition."""
    id: str
    name: str
    description: str
    pattern_id: str
    parameter_id: str
    steps: List[Dict[str, Any]]


# Response Models
class BaseResponse(BaseModel):
    """Base response model."""
    message: str


class PatternResponse(BaseModel):
    """Pattern response."""
    pattern: Pattern


class PatternListResponse(BaseModel):
    """Pattern list response."""
    patterns: List[Pattern]


class ParameterResponse(BaseModel):
    """Parameter response."""
    parameter: Parameter


class ParameterListResponse(BaseModel):
    """Parameter list response."""
    parameters: List[Parameter]


class SequenceResponse(BaseModel):
    """Sequence response."""
    sequence: Sequence


class SequenceListResponse(BaseModel):
    """Sequence list response."""
    sequences: List[Sequence]


class StatusType(str, Enum):
    """Status types."""
    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    ABORTED = "aborted"


class StatusResponse(BaseModel):
    """Status response."""
    status: StatusType
    details: Optional[Dict[str, Any]] = None


class NozzleResponse(BaseModel):
    """Nozzle response."""
    nozzle: Nozzle


class NozzleListResponse(BaseModel):
    """List of nozzles response."""
    nozzles: List[Nozzle]


class PowderResponse(BaseModel):
    """Powder response."""
    powder: Powder


class PowderListResponse(BaseModel):
    """List of powders response."""
    powders: List[Powder]
