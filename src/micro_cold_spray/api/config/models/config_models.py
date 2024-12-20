"""Configuration models."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ConfigRequest(BaseModel):
    """Configuration request model."""

    data: Dict[str, Any] = Field(
        ...,
        description="Configuration data"
    )
    format: str = Field(
        default="json",
        description="Format type (json or yaml)"
    )


class ConfigResponse(BaseModel):
    """Configuration response model."""

    name: str = Field(
        ...,
        description="Configuration name"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Configuration data"
    )
    format: str = Field(
        ...,
        description="Format type"
    )


class SchemaRequest(BaseModel):
    """Schema request model."""

    schema: Dict[str, Any] = Field(
        ...,
        description="JSON schema definition"
    )


class SchemaResponse(BaseModel):
    """Schema response model."""

    name: str = Field(
        ...,
        description="Schema name"
    )
    schema: Dict[str, Any] = Field(
        ...,
        description="JSON schema definition"
    )


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(
        ...,
        description="Service status (healthy/unhealthy)"
    )
    is_healthy: bool = Field(
        ...,
        description="Whether service is healthy"
    )
    services: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Service health details"
    )


class MessageResponse(BaseModel):
    """Generic message response model."""

    message: str = Field(
        ...,
        description="Response message"
    )
