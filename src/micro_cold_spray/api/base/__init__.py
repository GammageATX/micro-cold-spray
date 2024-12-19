"""Base module for micro cold spray API."""

from .base_service import BaseService
from .base_configurable import ConfigurableService
from .base_app import BaseApp
from .base_router import BaseRouter
from .base_errors import (
    BaseError,
    ServiceError,
    ConfigError,
    ValidationError,
    AppErrorCode
)
from .base_registry import (
    get_service,
    register_service,
    get_service_by_name,
    clear_services,
    _services  # Expose for testing
)

__all__ = [
    'BaseService',
    'ConfigurableService',
    'BaseApp',
    'BaseRouter',
    'BaseError',
    'ServiceError',
    'ConfigError',
    'ValidationError',
    'AppErrorCode',
    'get_service',
    'register_service',
    'get_service_by_name',
    'clear_services',
    '_services'  # Expose for testing
]
