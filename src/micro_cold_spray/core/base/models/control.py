"""Service control models."""

from enum import Enum
from pydantic import BaseModel, Field


class ServiceAction(str, Enum):
    """Valid service control actions."""
    
    START = "start"
    STOP = "stop"
    RESTART = "restart"


class ControlRequest(BaseModel):
    """Service control request model."""
    
    action: ServiceAction = Field(description="Control action to perform")


class ControlResponse(BaseModel):
    """Service control response model."""
    
    status: str = Field(description="Result status (success, error)")
    message: str = Field(description="Response message")
    error: str | None = Field(None, description="Error message if any")
