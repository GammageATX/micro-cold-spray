"""State management models."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StateCondition:
    """State transition condition."""
    tag: str
    type: str
    value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class StateConfig:
    """State configuration."""
    name: str
    valid_transitions: List[str]
    conditions: Dict[str, StateCondition]
    description: Optional[str] = None


@dataclass
class StateTransition:
    """State transition record."""
    old_state: str
    new_state: str
    timestamp: datetime
    reason: str
    conditions_met: Dict[str, bool]


@dataclass
class StateRequest:
    """State change request."""
    target_state: str
    reason: Optional[str] = None
    force: bool = False


@dataclass
class StateResponse:
    """State change response."""
    success: bool
    old_state: str
    new_state: Optional[str] = None
    error: Optional[str] = None
    failed_conditions: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
