"""Process models."""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ProcessState(BaseModel):
    """Process state model."""
    process_id: str = Field(..., description="Unique process identifier")
    state: str = Field(..., description="Current process state")
    timestamp: datetime = Field(default_factory=datetime.now, description="State timestamp")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Process parameters")


class ProcessRequest(BaseModel):
    """Process request model."""
    process_id: str = Field(..., description="Unique process identifier")
    action: str = Field(..., description="Requested process action")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Process parameters")


class ProcessResponse(BaseModel):
    """Process response model."""
    process_id: str = Field(..., description="Unique process identifier")
    status: str = Field(..., description="Process status")
    message: str = Field(..., description="Process message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Process data")
