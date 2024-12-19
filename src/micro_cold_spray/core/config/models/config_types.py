"""Configuration type definitions."""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ConfigType(str, Enum):
    """Available configuration types."""
    APPLICATION = "application"
    HARDWARE = "hardware"
    PROCESS = "process"
    STATE = "state"
    TAGS = "tags"


class ConfigData(BaseModel):
    """Simple configuration data model."""
    config_type: ConfigType = Field(..., description="Type of configuration")
    data: Dict[str, Any] = Field(..., description="Configuration data")
    version: str = Field(default="1.0.0", description="Configuration version")


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    data: Dict[str, Any] = Field(..., description="New configuration data")
    description: Optional[str] = Field(None, description="Optional update description")
