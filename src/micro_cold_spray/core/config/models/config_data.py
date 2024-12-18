"""Configuration data models."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ConfigMetadata(BaseModel):
    """Configuration metadata."""

    config_type: str = Field(description="Type of configuration")
    last_modified: datetime = Field(description="Last modification timestamp")


class ConfigData(BaseModel):
    """Configuration data with metadata."""

    metadata: ConfigMetadata = Field(description="Configuration metadata")
    data: Dict[str, Any] = Field(description="Configuration data")


class ConfigUpdate(BaseModel):
    """Configuration update request."""

    config_type: str = Field(description="Type of configuration to update")
    data: Dict[str, Any] = Field(description="New configuration data")
    backup: bool = Field(default=True, description="Whether to create backup")
    should_validate: bool = Field(default=True, description="Whether to validate data")


class ConfigValidationResult(BaseModel):
    """Configuration validation result."""

    valid: bool = Field(description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class ConfigFieldInfo(BaseModel):
    """Configuration field information."""

    name: str = Field(description="Field name")
    path: str = Field(description="JSON path to field")
    type: str = Field(description="Field type")
    description: Optional[str] = Field(None, description="Field description")
    required: bool = Field(description="Whether field is required")
    default: Optional[Any] = Field(None, description="Default value")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Field constraints")


class TagRemapRequest(BaseModel):
    """Tag remapping request."""

    old_tag: str = Field(description="Old tag name")
    new_tag: str = Field(description="New tag name")
    should_validate: bool = Field(default=True, description="Whether to validate new tag")
