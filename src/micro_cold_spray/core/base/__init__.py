"""Base package for core functionality."""

from .services.base_service import BaseService
from .services.configurable_service import ConfigurableService
from .models.health import HealthResponse
from .router import add_health_endpoints, get_service_from_app, get_service, create_service_dependency

__all__ = [
    'BaseService',
    'ConfigurableService',
    'HealthResponse',
    'add_health_endpoints',
    'get_service_from_app',
    'get_service',
    'create_service_dependency'
]
