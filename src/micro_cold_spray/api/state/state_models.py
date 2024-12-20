"""State management models."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class StateCondition(BaseModel):
    """State transition condition."""
    tag: str = Field(..., description="Tag name to monitor")
    type: str = Field(..., description="Condition type (equals, not_equals, greater_than, less_than, in_range)")
    value: Any = Field(..., description="Expected value")
    min_value: Optional[float] = Field(None, description="Minimum value for range check")
    max_value: Optional[float] = Field(None, description="Maximum value for range check")


class StateConfig(BaseModel):
    """State configuration."""
    name: str = Field(..., description="State name")
    valid_transitions: List[str] = Field(..., description="List of valid target states")
    conditions: Dict[str, StateCondition] = Field(default_factory=dict, description="State transition conditions")
    description: Optional[str] = Field(None, description="State description")


class StateTransition(BaseModel):
    """State transition record."""
    old_state: str = Field(..., description="Previous state")
    new_state: str = Field(..., description="New state")
    timestamp: datetime = Field(..., description="Transition timestamp")
    reason: str = Field(..., description="Transition reason")
    conditions_met: Dict[str, bool] = Field(default_factory=dict, description="Conditions status at transition")


class StateRequest(BaseModel):
    """State change request."""
    target_state: str = Field(..., description="Target state to transition to")
    reason: Optional[str] = Field(None, description="Reason for state change")
    force: bool = Field(False, description="Force transition without checking conditions")


class StateResponse(BaseModel):
    """State change response."""
    success: bool = Field(..., description="Whether transition was successful")
    old_state: str = Field(..., description="Previous state")
    new_state: Optional[str] = Field(None, description="New state if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    failed_conditions: Optional[List[str]] = Field(None, description="List of failed conditions")
    timestamp: Optional[datetime] = Field(None, description="Transition timestamp")
