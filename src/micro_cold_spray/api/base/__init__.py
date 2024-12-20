"""Base module for micro cold spray API."""

from .base_service import BaseService
from .base_configurable import ConfigurableService
from .base_app import BaseApp
from .base_router import BaseRouter
from .base_errors import create_http_error
from .base_registry import (
    get_service,
    register_service,
    clear_services,
    _services  # Expose for testing
)

__all__ = [
    'BaseService',
    'ConfigurableService',
    'BaseApp',
    'BaseRouter',
    'create_http_error',
    'get_service',
    'register_service',
    'clear_services',
    '_services'  # Expose for testing
]
