"""Health check utilities."""

from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel


def get_uptime(start_time: Optional[datetime]) -> float:
    """Get uptime in seconds since start time.
    
    Args:
        start_time: Start time or None
        
    Returns:
        Uptime in seconds or 0.0 if not started
    """
    if start_time is None:
        return 0.0
    return (datetime.now() - start_time).total_seconds()


class ComponentHealth(BaseModel):
    """Component health status."""
    
    status: str  # ok or error
    error: Optional[str] = None


class ServiceHealth(BaseModel):
    """Service health status."""
    
    status: str  # ok or error
    service: str
    version: str
    is_running: bool
    uptime: float
    error: Optional[str] = None
    components: Dict[str, ComponentHealth]
