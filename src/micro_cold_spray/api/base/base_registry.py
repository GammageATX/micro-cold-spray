"""Service registry module."""

from typing import Dict, TypeVar, Type, Callable, cast, Set

from micro_cold_spray.api.base.base_errors import ServiceError, AppErrorCode
from micro_cold_spray.api.base.base_service import BaseService

T = TypeVar("T", bound=BaseService)
_services: Dict[Type[BaseService], BaseService] = {}
_services_by_name: Dict[str, BaseService] = {}


def register_service(service: BaseService) -> None:
    """Register service instance.
    
    Args:
        service: Service instance to register
        
    Raises:
        TypeError: If service is not an instance of BaseService
        ServiceError: If service dependencies form a cycle
    """
    if not isinstance(service, BaseService):
        raise TypeError("Service must be an instance of BaseService")
        
    # Check for dependency cycles
    if service.dependencies:
        visited: Set[str] = set()
        path: Set[str] = set()
        
        def check_cycle(service_name: str) -> None:
            if service_name in path:
                raise ServiceError(
                    f"Dependency cycle detected: {service_name}",
                    error_code=AppErrorCode.SERVICE_ERROR
                )
                
            # Skip if we've already checked this service
            if service_name in visited:
                return
                
            # Add to current path
            path.add(service_name)
            
            # Get dependencies for this service
            deps = []
            if service._service_name == service_name:
                deps = service.dependencies
            elif service_name in _services_by_name:
                deps = _services_by_name[service_name].dependencies
                
            # Check each dependency
            for dep in deps:
                check_cycle(dep)
                    
            # Remove from current path
            path.remove(service_name)
            visited.add(service_name)
            
        check_cycle(service._service_name)
        
    _services[type(service)] = service
    _services_by_name[service._service_name] = service


def get_service(service_type: Type[T]) -> Callable[[], T]:
    """Get service instance factory.
    
    Args:
        service_type: Type of service to get
        
    Returns:
        Service instance factory
        
    Raises:
        RuntimeError: If service not found or has wrong type
    """
    def _get_service_instance() -> T:
        # Check if service type is registered directly
        if service_type in _services:
            return cast(T, _services[service_type])

        # Check if a registered service is a subclass of the requested type
        for registered_type, service in _services.items():
            if issubclass(registered_type, service_type):
                return cast(T, service)

        # Check if a registered service is an instance of the requested type
        for service in _services.values():
            if isinstance(service, service_type):
                return cast(T, service)

        raise RuntimeError(f"Service {service_type.__name__} not initialized")

    return _get_service_instance


def get_service_by_name(service_name: str) -> BaseService:
    """Get service instance by name.
    
    Args:
        service_name: Name of service to get
        
    Returns:
        Service instance
        
    Raises:
        ServiceError: If service not found
    """
    if service_name in _services_by_name:
        return _services_by_name[service_name]
            
    raise ServiceError(
        f"Service {service_name} not initialized",
        error_code=AppErrorCode.SERVICE_NOT_FOUND
    )


def clear_services() -> None:
    """Clear all registered services."""
    _services.clear()
    _services_by_name.clear()
