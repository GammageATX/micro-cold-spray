"""Health check models."""

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(description="Service health status (ok, error, degraded)")
    service_name: str = Field(description="Name of the service")
    version: str = Field(description="Service version")
    is_running: bool = Field(description="Whether service is running")
    is_ready: bool = True  # Default to True for backward compatibility
    error: Optional[str] = Field(None, description="Error message if any")
    message: Optional[str] = Field(None, description="Status message if any")
    uptime: Optional[float] = Field(None, description="Service uptime if running")
