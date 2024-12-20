"""Base registry module."""

from typing import Dict, Type, Union

from .base_service import BaseService


# Global service registry
_services: Dict[str, BaseService] = {}


def register_service(service: BaseService) -> None:
    """Register service instance.
    
    Args:
        service: Service instance to register
    
    Raises:
        ValueError: If service is already registered
    """
    if service.name in _services:
        raise ValueError(f"Service {service.name} is already registered")
    _services[service.name] = service


def get_service(service_type_or_name: Union[Type[BaseService], str]) -> BaseService:
    """Get service instance by type or name.
    
    Args:
        service_type_or_name: Service type or name to get
    
    Returns:
        Service instance
    
    Raises:
        ValueError: If service not found
    """
    # Handle string service names
    if isinstance(service_type_or_name, str):
        if service_type_or_name not in _services:
            raise ValueError(f"Service {service_type_or_name} not found")
        return _services[service_type_or_name]
    
    # Handle service types
    for service in _services.values():
        if isinstance(service, service_type_or_name):
            return service
    
    raise ValueError(f"Service of type {service_type_or_name.__name__} not found")


def clear_services() -> None:
    """Clear all registered services."""
    _services.clear()
