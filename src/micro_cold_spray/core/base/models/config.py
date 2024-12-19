"""Base configuration models."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class BaseSettings(BaseModel):
    """Base settings model for all services."""

    version: str = Field(
        default="1.0.0",
        description="Service version"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )


class ServiceSettings(BaseSettings):
    """Base settings model for configurable services."""

    enabled: bool = Field(
        default=True,
        description="Whether the service is enabled"
    )
    config_type: Optional[str] = Field(
        default=None,
        description="Type of configuration to load"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Service-specific configuration"
    )
