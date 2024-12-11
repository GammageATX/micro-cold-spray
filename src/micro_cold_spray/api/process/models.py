"""Process data models."""

from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime


@dataclass
class ActionGroup:
    """Action group definition."""
    name: str
    actions: List[Dict[str, Any]]
    parameters: Dict[str, Any]


@dataclass
class SequenceMetadata:
    """Sequence metadata."""
    name: str
    version: str
    created: datetime
    description: str | None = None


@dataclass
class SequenceStep:
    """Sequence step definition."""
    action_group: str | None = None
    pattern: str | None = None
    parameters: Dict[str, Any] | None = None
    modifications: Dict[str, Any] | None = None
