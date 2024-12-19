"""Configuration service package."""

from micro_cold_spray.api.config.config_app import ConfigApp, create_app
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.models import (
    ConfigData,
    ConfigMetadata,
    ConfigUpdate,
    ConfigValidationResult,
    ConfigFieldInfo,
    TagRemapRequest,
    SchemaRegistry
)
from micro_cold_spray.api.config.utils import (
    get_config_service,
    set_config_service
)
from micro_cold_spray.api.config.endpoints import router

__all__ = [
    # Main components
    "ConfigApp",
    "ConfigService",
    "router",
    # Models
    "ConfigData",
    "ConfigMetadata",
    "ConfigUpdate",
    "ConfigValidationResult",
    "ConfigFieldInfo",
    "TagRemapRequest",
    "SchemaRegistry",
    # Factory functions
    "create_app",
    # Utilities
    "get_config_service",
    "set_config_service"
]
