"""Configuration API models."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status (ok or error)")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    is_running: bool = Field(..., description="Whether service is running")
    uptime: float = Field(..., description="Service uptime in seconds")
    memory_usage: Dict[str, float] = Field(..., description="Memory usage stats")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class MessageResponse(BaseModel):
    """Generic message response model."""
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ConfigRequest(BaseModel):
    """Configuration request model."""
    name: str = Field(..., description="Configuration name")
    format: str = Field(..., description="Configuration format (json or yaml)")
    schema_name: Optional[str] = Field(None, description="Schema name for validation")
    data: Dict[str, Any] = Field(..., description="Configuration data")


class ConfigResponse(BaseModel):
    """Configuration response model."""
    name: str = Field(..., description="Configuration name")
    format: str = Field(..., description="Configuration format")
    schema_name: Optional[str] = Field(None, description="Schema name")
    data: Dict[str, Any] = Field(..., description="Configuration data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class SchemaRequest(BaseModel):
    """Schema request model."""
    name: str = Field(..., description="Schema name")
    schema_definition: Dict[str, Any] = Field(..., description="JSON schema definition")


class SchemaResponse(BaseModel):
    """Schema response model."""
    name: str = Field(..., description="Schema name")
    schema_definition: Dict[str, Any] = Field(..., description="JSON schema definition")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ConfigListResponse(BaseModel):
    """Configuration list response model."""
    configs: List[str] = Field(..., description="List of configuration names")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class SchemaListResponse(BaseModel):
    """Schema list response model."""
    schemas: List[str] = Field(..., description="List of schema names")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
