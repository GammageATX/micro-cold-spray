"""Base components for all APIs."""

from typing import Type, TypeVar, Callable

from .service import BaseService
from .configurable import ConfigurableService
from .exceptions import APIError, ServiceError, ValidationError

# Type variable for service types
T = TypeVar('T', bound=BaseService)

# Service instances
_services: dict = {}


def get_service(service_type: Type[T]) -> Callable[[], T]:
    """Get service instance by type.
    
    Args:
        service_type: Type of service to get
        
    Returns:
        Dependency function that returns service instance
        
    Raises:
        RuntimeError: If service not initialized
    """
    def _get_service_instance() -> T:
        if service_type not in _services:
            raise RuntimeError(f"Service {service_type.__name__} not initialized")
        return _services[service_type]
    
    return _get_service_instance


def register_service(service: BaseService) -> None:
    """Register a service instance."""
    _services[type(service)] = service


__all__ = [
    "BaseService",
    "ConfigurableService",
    "APIError",
    "ServiceError",
    "ValidationError",
    "get_service",
    "register_service"
]
