"""Configuration API models."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


# Base response model
class BaseResponse(BaseModel):
    """Base response model with timestamp."""
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


# Message response
class MessageResponse(BaseResponse):
    """Generic message response model."""
    message: str = Field(..., description="Response message")


# Config endpoints
class ConfigRequest(BaseModel):
    """Configuration request model."""
    format: str = Field(..., description="Configuration format (json or yaml)")
    data: Dict[str, Any] = Field(..., description="Configuration data")


class ConfigResponse(BaseResponse):
    """Configuration response model."""
    name: str = Field(..., description="Configuration name")
    format: str = Field(..., description="Configuration format")
    schema_name: Optional[str] = Field(None, description="Schema name")
    data: Dict[str, Any] = Field(..., description="Configuration data")


class ConfigListResponse(BaseResponse):
    """Configuration list response model."""
    configs: List[str] = Field(..., description="List of configuration names")


# Schema endpoints
class SchemaRequest(BaseModel):
    """Schema request model."""
    schema_definition: Dict[str, Any] = Field(..., description="JSON schema definition")


class SchemaResponse(BaseResponse):
    """Schema response model."""
    name: str = Field(..., description="Schema name")
    schema_definition: Dict[str, Any] = Field(..., description="JSON schema definition")


class SchemaListResponse(BaseResponse):
    """Schema list response model."""
    schemas: List[str] = Field(..., description="List of schema names")
