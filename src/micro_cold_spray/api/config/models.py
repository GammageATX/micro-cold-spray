"""Configuration data models."""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class ConfigMetadata:
    """Configuration metadata."""
    config_type: str
    last_modified: datetime
    version: str = "1.0.0"
    description: Optional[str] = None


@dataclass
class ConfigData:
    """Configuration data container."""
    metadata: ConfigMetadata
    data: Dict[str, Any]


@dataclass
class ConfigUpdate:
    """Configuration update request."""
    config_type: str
    data: Dict[str, Any]
    backup: bool = True
    validate: bool = True


@dataclass
class ConfigStatus:
    """Configuration service status."""
    is_running: bool
    cache_size: int
    last_error: Optional[str] = None
    last_update: Optional[datetime] = None
