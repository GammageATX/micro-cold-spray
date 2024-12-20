"""Base API components.

This module provides the core building blocks for the micro cold spray API:

- BaseService: Base class for all services with lifecycle management
- ConfigurableService: Mixin for services that require configuration
- BaseApp: FastAPI application with service management
- BaseRouter: Router with health check endpoints
- create_error: Utility for creating consistent HTTP errors
- register_service/get_service: Service registry utilities
"""

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_app import BaseApp
from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_registry import (
    register_service,
    get_service,
    clear_services,
)

__all__ = [
    "BaseService",
    "ConfigurableService",
    "BaseApp",
    "BaseRouter",
    "create_error",
    "register_service",
    "get_service",
    "clear_services",
]
