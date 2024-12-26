"""Health check utilities and models."""

import time
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field


# Uptime tracking
_start_time = time.time()


def get_uptime() -> float:
    """Get service uptime in seconds.
    
    Returns:
        Uptime in seconds
    """
    return time.time() - _start_time


class ComponentHealth(BaseModel):
    """Component health status."""
    status: str = Field(..., description="Component status (ok or error)")
    error: Optional[str] = Field(None, description="Error message if any")


class ServiceHealth(BaseModel):
    """Standardized health check response model."""
    status: str = Field(..., description="Service status (ok or error)")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    is_running: bool = Field(..., description="Whether service is running")
    uptime: float = Field(..., description="Service uptime in seconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    error: Optional[str] = Field(None, description="Error message if any")
    mode: Optional[str] = Field(None, description="Service mode (e.g., mock, hardware)")
    components: Optional[Dict[str, ComponentHealth]] = Field(None, description="Component health statuses")
