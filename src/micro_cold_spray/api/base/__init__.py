"""Base module for micro cold spray API."""

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_app import BaseApp
from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_registry import (
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
    'create_error',
    'get_service',
    'register_service',
    'clear_services',
    '_services'  # Expose for testing
]
