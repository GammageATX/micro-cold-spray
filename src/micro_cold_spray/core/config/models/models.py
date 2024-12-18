"""Configuration models."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator, model_validator
from enum import Enum


class ConfigType(str, Enum):
    """Available configuration types."""
    APPLICATION = "application"
    HARDWARE = "hardware"
    PROCESS = "process"
    STATE = "state"
    TAGS = "tags"
    FILE_FORMAT = "file_format"


class ConfigMetadata(BaseModel):
    """Configuration metadata model."""
    config_type: ConfigType = Field(
        ...,
        description="Type of configuration"
    )
    last_modified: datetime = Field(
        default_factory=datetime.now,
        description="Last modification timestamp"
    )
    version: str = Field(
        ...,
        description="Configuration version",
        pattern=r"^\d+\.\d+\.\d+$"
    )
    description: Optional[str] = Field(
        None,
        description="Optional configuration description"
    )

    @validator("version")
    def validate_version(cls, v: str) -> str:
        """Validate version format."""
        if not v:
            raise ValueError("Version cannot be empty")
        parts = v.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError("Version must be in format X.Y.Z")
        return v


class ConfigValidationResult(BaseModel):
    """Configuration validation result model."""
    valid: bool = Field(
        ...,
        description="Whether the configuration is valid"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of validation warnings"
    )

    @model_validator(mode='after')
    def check_validation_state(self) -> 'ConfigValidationResult':
        """Ensure validation state is consistent."""
        if self.valid and self.errors:
            raise ValueError("Cannot be valid with errors")
        if not self.valid and not self.errors:
            raise ValueError("Must have errors if not valid")
        return self


class ConfigData(BaseModel):
    """Configuration data model."""
    metadata: ConfigMetadata = Field(
        ...,
        description="Configuration metadata"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Configuration data"
    )

    @validator("data")
    def validate_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration data."""
        if not v:
            raise ValueError("Configuration data cannot be empty")
        return v


class ConfigUpdateRequest(BaseModel):
    """Configuration update request model."""
    config: Dict[str, Any] = Field(
        ...,
        description="New configuration data"
    )
    description: Optional[str] = Field(
        None,
        description="Optional update description"
    )

    @validator("config")
    def validate_config(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate update request data."""
        if not v:
            raise ValueError("Configuration data cannot be empty")
        return v


class ConfigResponse(BaseModel):
    """Configuration response model."""
    config: Dict[str, Any] = Field(
        ...,
        description="Configuration data"
    )
    metadata: ConfigMetadata = Field(
        ...,
        description="Configuration metadata"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "config": {
                    "setting1": "value1",
                    "setting2": 42
                },
                "metadata": {
                    "config_type": "application",
                    "version": "1.0.0",
                    "last_modified": "2024-01-01T00:00:00",
                    "description": "Example configuration"
                }
            }
        }
    }


class ConfigTypeInfo(BaseModel):
    """Configuration type information model."""
    id: ConfigType = Field(
        ...,
        description="Configuration type identifier"
    )
    name: str = Field(
        ...,
        description="Human-readable name"
    )
    description: Optional[str] = Field(
        None,
        description="Optional type description"
    )
    json_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON schema for validation"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "application",
                "name": "Application Configuration",
                "description": "Application-wide settings",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "setting1": {"type": "string"},
                        "setting2": {"type": "integer"}
                    }
                }
            }
        }
    }


class ConfigTypesResponse(BaseModel):
    """Configuration types response model."""
    types: List[ConfigTypeInfo] = Field(
        ...,
        description="List of available configuration types"
    )

    @validator("types")
    def validate_types(cls, v: List[ConfigTypeInfo]) -> List[ConfigTypeInfo]:
        """Validate configuration types list."""
        if not v:
            raise ValueError("Configuration types list cannot be empty")
        return v


class UpdateConfigResponse(BaseModel):
    """Configuration update response model."""
    status: str = Field(
        ...,
        description="Update status (updated, error)"
    )
    validation: ConfigValidationResult = Field(
        ...,
        description="Validation results"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "updated",
                "validation": {
                    "valid": True,
                    "errors": [],
                    "warnings": []
                }
            }
        }
    }


class CacheResponse(BaseModel):
    """Cache operation response model."""
    status: str = Field(
        ...,
        description="Operation status (cleared, error)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "cleared"
            }
        }
    }


class SchemaRegistry(BaseModel):
    """Schema registry model."""
    schemas: Dict[ConfigType, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Mapping of config types to their JSON schemas"
    )

    @validator("schemas")
    def validate_schemas(cls, v: Dict[ConfigType, Dict[str, Any]]) -> Dict[ConfigType, Dict[str, Any]]:
        """Validate schema registry."""
        if not v:
            raise ValueError("Schema registry cannot be empty")
        return v


class ConfigFieldInfo(BaseModel):
    """Configuration field information model."""
    name: str = Field(
        ...,
        description="Field name"
    )
    type: str = Field(
        ...,
        description="Field type"
    )
    description: Optional[str] = Field(
        None,
        description="Field description"
    )
    required: bool = Field(
        default=False,
        description="Whether the field is required"
    )
    default: Optional[Any] = Field(
        None,
        description="Default value if any"
    )
    constraints: Optional[Dict[str, Any]] = Field(
        None,
        description="Field constraints"
    )


class ConfigUpdate(BaseModel):
    """Configuration update model."""
    config_type: ConfigType = Field(
        ...,
        description="Type of configuration to update"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="New configuration data"
    )
    should_validate: bool = Field(
        default=True,
        description="Whether to validate the update"
    )
    backup: bool = Field(
        default=True,
        description="Whether to create a backup"
    )

    @validator("data")
    def validate_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate update data."""
        if not v:
            raise ValueError("Configuration data cannot be empty")
        return v


class TagRemapRequest(BaseModel):
    """Tag remapping request model."""
    old_tag: str = Field(
        ...,
        description="Original tag name"
    )
    new_tag: str = Field(
        ...,
        description="New tag name"
    )
    should_validate: bool = Field(
        default=True,
        description="Whether to validate the new tag"
    )

    @validator("old_tag", "new_tag")
    def validate_tags(cls, v: str) -> str:
        """Validate tag names."""
        if not v:
            raise ValueError("Tag name cannot be empty")
        if not v.isidentifier():
            raise ValueError("Tag name must be a valid identifier")
        return v


class FormatMetadata(BaseModel):
    """Format metadata model."""
    description: str = Field(
        ...,
        description="Description of the format"
    )
    examples: List[str] = Field(
        ...,
        description="Example values in this format"
    )

    @validator("examples")
    def validate_examples(cls, v: List[str]) -> List[str]:
        """Validate examples list."""
        if not v:
            raise ValueError("Must provide at least one example")
        return v


class ConfigSchema(BaseModel):
    """Configuration schema model."""
    type: str = Field(
        ...,
        description="Schema type (object, array, string, number, boolean)"
    )
    description: Optional[str] = Field(
        None,
        description="Schema description"
    )
    required: Optional[List[str]] = Field(
        None,
        description="List of required fields (for object type)"
    )
    properties: Optional[Dict[str, 'ConfigSchema']] = Field(
        None,
        description="Object properties (for object type)"
    )
    items: Optional['ConfigSchema'] = Field(
        None,
        description="Array item schema (for array type)"
    )
    pattern: Optional[str] = Field(
        None,
        description="Regex pattern (for string type)"
    )
    enum: Optional[List[Any]] = Field(
        None,
        description="List of allowed values"
    )
    minimum: Optional[float] = Field(
        None,
        description="Minimum value (for number type)"
    )
    maximum: Optional[float] = Field(
        None,
        description="Maximum value (for number type)"
    )
    allow_unknown: bool = Field(
        default=False,
        description="Whether to allow unknown fields in objects"
    )

    @validator("type")
    def validate_type(cls, v: str) -> str:
        """Validate schema type."""
        allowed_types = {"object", "array", "string", "number", "boolean"}
        if v not in allowed_types:
            raise ValueError(f"Invalid schema type. Must be one of: {allowed_types}")
        return v

    @validator("properties")
    def validate_properties(cls, v: Optional[Dict[str, 'ConfigSchema']], values: Dict[str, Any]) -> Optional[Dict[str, 'ConfigSchema']]:
        """Validate properties field."""
        if values.get("type") == "object" and not v:
            raise ValueError("Object type schema must have properties")
        return v

    @validator("items")
    def validate_items(cls, v: Optional['ConfigSchema'], values: Dict[str, Any]) -> Optional['ConfigSchema']:
        """Validate items field."""
        if values.get("type") == "array" and not v:
            raise ValueError("Array type schema must have items")
        return v
