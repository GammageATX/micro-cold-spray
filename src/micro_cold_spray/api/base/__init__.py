"""Base API package."""

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_registry import (
    register_service,
    get_service,
    clear_services
)
from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.base.base_app import create_app

__all__ = [
    'create_app',
    'BaseService',
    'ConfigurableService',
    'BaseRouter',
    'create_error',
    'register_service',
    'get_service',
    'clear_services'
]
