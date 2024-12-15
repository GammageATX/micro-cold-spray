"""Configuration data models."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class FormatMetadata(BaseModel):
    """Metadata for format validators."""
    description: str
    examples: List[str]


class ConfigSchema(BaseModel):
    """Schema definition for config validation."""
    type: str = Field(description="Basic types: string, number, boolean, object, array")
    title: Optional[str] = None
    required: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    enum: Optional[List[Any]] = None
    pattern: Optional[str] = None
    properties: Optional[Dict[str, 'ConfigSchema']] = None
    items: Optional['ConfigSchema'] = None
    description: Optional[str] = None
    format: Optional[str] = None
    references: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    allow_unknown: bool = False

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed_types = {'string', 'number', 'boolean', 'object', 'array', 'state', 'tag', 'action', 'sequence'}
        if v not in allowed_types:
            raise ValueError(f'Type must be one of {allowed_types}')
        return v


class SchemaRegistry(BaseModel):
    """Registry of known config schemas."""
    application: ConfigSchema
    hardware: ConfigSchema
    process: ConfigSchema
    tags: ConfigSchema
    state: ConfigSchema
    file_format: ConfigSchema


class ConfigReference(BaseModel):
    """Reference to another config value."""
    config_type: str
    path: str
    required: bool = True


class ConfigValidationResult(BaseModel):
    """Result of config validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]


class ConfigMetadata(BaseModel):
    """Configuration metadata."""
    config_type: str
    last_modified: datetime
    version: str = "1.0.0"
    description: Optional[str] = None
    json_schema: Optional[ConfigSchema] = None


class ConfigData(BaseModel):
    """Configuration data container."""
    metadata: ConfigMetadata
    data: Dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from config data with optional default."""
        if not isinstance(self.data, dict):
            return default
            
        keys = key.split(".")
        current = self.data
        
        for k in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(k, default)
            if current == default:
                return default
                
        return current


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    config_type: str
    data: Dict[str, Any]
    backup: bool = True
    should_validate: bool = True


class ConfigStatus(BaseModel):
    """Configuration service status."""
    is_running: bool
    cache_size: int
    last_error: Optional[str] = None
    last_update: Optional[datetime] = None


class TagRemapRequest(BaseModel):
    """Request to remap a tag."""
    old_tag: str
    new_tag: str
    should_validate: bool = True


class ConfigFieldInfo(BaseModel):
    """Information about an editable config field."""
    path: str
    type: str
    description: str
    constraints: Dict[str, Any]
    current_value: Any
