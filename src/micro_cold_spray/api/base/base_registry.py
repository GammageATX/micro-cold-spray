"""Base registry module."""

from typing import Dict, Type, Union
from fastapi import status

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error


# Global service registry
_services: Dict[str, BaseService] = {}


def register_service(service: BaseService) -> None:
    """Register service instance.
    
    Args:
        service: Service instance to register
    
    Raises:
        HTTPException: If service is already registered
    """
    if service.name in _services:
        raise create_error(
            status_code=status.HTTP_409_CONFLICT,
            message=f"Service {service.name} is already registered",
            context={"service": service.name}
        )
    _services[service.name] = service


def get_service(service_type_or_name: Union[Type[BaseService], str]) -> BaseService:
    """Get service instance by type or name.
    
    Args:
        service_type_or_name: Service type or name to get
    
    Returns:
        Service instance
    
    Raises:
        HTTPException: If service not found
    """
    # Handle string service names
    if isinstance(service_type_or_name, str):
        if service_type_or_name not in _services:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Service {service_type_or_name} not found",
                context={"service": service_type_or_name}
            )
        return _services[service_type_or_name]
    
    # Handle service types
    for service in _services.values():
        if isinstance(service, service_type_or_name):
            return service
    
    raise create_error(
        status_code=status.HTTP_404_NOT_FOUND,
        message=f"Service of type {service_type_or_name.__name__} not found",
        context={"service_type": service_type_or_name.__name__}
    )


def clear_services() -> None:
    """Clear all registered services."""
    _services.clear()
