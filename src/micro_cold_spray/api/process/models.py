"""Process data models."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class ActionGroup:
    """Action group definition."""
    name: str
    actions: List[Dict[str, Any]]
    parameters: Dict[str, Any]
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: Optional[datetime] = None


@dataclass
class SequenceMetadata:
    """Sequence metadata."""
    name: str
    version: str
    created: datetime
    description: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    modified: Optional[datetime] = None


@dataclass
class SequenceStep:
    """Sequence step definition."""
    action_group: Optional[str] = None
    pattern: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    modifications: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    timeout: Optional[float] = None
    retry_count: int = 0


@dataclass
class ProcessPattern:
    """Process pattern definition."""
    name: str
    type: str
    parameters: Dict[str, Any]
    points: List[Dict[str, float]]
    metadata: SequenceMetadata
    preview_url: Optional[str] = None


@dataclass
class ParameterSet:
    """Process parameter set."""
    name: str
    parameters: Dict[str, Any]
    metadata: SequenceMetadata
    validation_rules: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionStatus:
    """Process execution status."""
    sequence_id: str
    status: str
    current_step: int
    total_steps: int
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    progress: float = 0.0
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionStatus:
    """Action execution status."""
    action_type: str
    parameters: Dict[str, Any]
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    progress: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
