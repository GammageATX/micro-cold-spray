"""Base registry module."""

from typing import Dict, Type, Union, TypeVar
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_service import BaseService


T = TypeVar("T", bound=BaseService)
_services: Dict[str, BaseService] = {}


def register_service(service: BaseService) -> None:
    """Register a service instance.
    
    Args:
        service: Service instance to register
        
    Raises:
        HTTPException: If service already registered (409)
    """
    if service.name in _services:
        raise create_error(
            message=f"Service {service.name} already registered",
            status_code=status.HTTP_409_CONFLICT,
            context={"service": service.name}
        )
    _services[service.name] = service


def get_service(service_ref: Union[str, Type[T]]) -> Union[BaseService, T]:
    """Get a service by name or type.
    
    Args:
        service_ref: Service name or type
        
    Returns:
        Service instance
        
    Raises:
        HTTPException: If service not found (404)
    """
    if isinstance(service_ref, str):
        if service_ref not in _services:
            raise create_error(
                message=f"Service {service_ref} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                context={"service": service_ref}
            )
        return _services[service_ref]
    
    # Look up by type
    for service in _services.values():
        if isinstance(service, service_ref):
            return service
    
    raise create_error(
        message=f"Service of type {service_ref.__name__} not found",
        status_code=status.HTTP_404_NOT_FOUND,
        context={"service_type": service_ref.__name__}
    )


async def clear_services() -> None:
    """Clear all registered services."""
    global _services
    
    # Stop all services
    for service in _services.values():
        try:
            if service.is_running:
                await service.stop()
        except Exception:
            pass  # Ignore stop errors during cleanup
    
    # Clear registry
    _services = {}
