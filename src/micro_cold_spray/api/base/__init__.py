"""Base components for all APIs."""

from typing import Type, TypeVar, Callable

from .service import BaseService
from .configurable import ConfigurableService
from .exceptions import ServiceError, ValidationError

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
        # Check if service type is registered directly
        if service_type in _services:
            return _services[service_type]
            
        # Check if a subclass is registered
        for registered_type, service in _services.items():
            if isinstance(service, service_type):
                return service
                
        raise RuntimeError(f"Service {service_type.__name__} not initialized")
    
    return _get_service_instance


def register_service(service: object) -> None:
    """Register a service instance.
    
    Args:
        service: Service instance to register
        
    Raises:
        TypeError: If service is not an instance of BaseService
    """
    if not isinstance(service, BaseService):
        raise TypeError("Service must be an instance of BaseService")
        
    # Register service with its actual type
    service_type = type(service)
    _services[service_type] = service
    
    # Also register with base types if they're not already registered
    for base in service_type.__mro__[1:]:  # Skip the class itself
        if base is object:
            break
        if issubclass(base, BaseService) and base not in _services:
            _services[base] = service


__all__ = [
    "BaseService",
    "ConfigurableService",
    "ServiceError",
    "ValidationError",
    "get_service",
    "register_service"
]
