"""Base router functionality.

This module provides core routing functionality for both BaseService (used by Config API)
and ConfigurableService (used by all other APIs).
"""

from typing import Type, TypeVar, Callable, Dict, Any, Optional
from fastapi import FastAPI, APIRouter, status, Request
from loguru import logger
from datetime import datetime

from micro_cold_spray.core.base.services.base_service import BaseService
from micro_cold_spray.core.base.services.configurable_service import ConfigurableService
from micro_cold_spray.core.base.models.health import HealthResponse
from micro_cold_spray.core.base.models.control import ControlRequest, ControlResponse, ServiceAction
from micro_cold_spray.core.errors.codes import (
    AppErrorCode, raise_http_error,
    ConfigurationError, ServiceError
)
from micro_cold_spray.core.errors.formatting import raise_http_error

# Type variable for service types
ServiceType = TypeVar('ServiceType', BaseService, ConfigurableService)


def get_service_from_app(app: FastAPI, service_type: Type[ServiceType]) -> ServiceType:
    """Get service instance from FastAPI app state.
    
    Args:
        app: FastAPI application instance
        service_type: Expected service type (BaseService or ConfigurableService)
    
    Returns:
        Service instance of the requested type
    
    Raises:
        HTTPException: If service is not initialized or of wrong type
    """
    service = getattr(app.state, "service", None)
    if not service or not isinstance(service, service_type):
        raise_http_error(
            AppErrorCode.SERVICE_UNAVAILABLE,
            f"Service {service_type.__name__} not initialized"
        )
    return service


def get_service(request: Request, service_type: Type[ServiceType]) -> ServiceType:
    """Get service instance from request.
    
    Args:
        request: FastAPI request instance
        service_type: Expected service type (BaseService or ConfigurableService)
    
    Returns:
        Service instance of the requested type
    
    Raises:
        HTTPException: If service is not initialized or of wrong type
    """
    return get_service_from_app(request.app, service_type)


def create_service_dependency(service_type: Type[ServiceType]) -> Callable[[Request], ServiceType]:
    """Create a FastAPI dependency for a service type.
    
    Args:
        service_type: The type of service to get
        
    Returns:
        A dependency function that returns the service instance
    """
    def get_service_dependency(request: Request) -> ServiceType:
        return get_service(request, service_type)
    return get_service_dependency


def add_health_endpoints(router: APIRouter, service: BaseService) -> None:
    """Add standard health check endpoints to router.
    
    Args:
        router: Router to add endpoints to
        service: Service instance to monitor
    """
    @router.get(
        "/health",
        response_model=HealthResponse,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "description": "Service is not running or not ready",
                "model": dict  # Use dict since error format is dynamic
            }
        }
    )
    async def health_check() -> HealthResponse:
        """Check service health status."""
        try:
            # First check if service is running
            if not service.is_running:
                raise_http_error(
                    AppErrorCode.SERVICE_UNAVAILABLE,
                    "Service is not running"
                )
            
            # Get detailed health status
            health = await service.check_health()
            
            # Extract service info
            service_info = health.get("service_info", {})
            is_ready = service_info.get("ready", True)  # Default to True for backward compatibility
            version = service_info.get("version", getattr(service, "version", "1.0.0"))
            
            # Convert timedelta to float seconds for uptime
            uptime = service_info.get("uptime")
            if uptime is not None:
                uptime = uptime.total_seconds()
            
            # Extract error and message
            error = health.get("error")
            message = health.get("message")
            
            # If there are failing services, include their errors in the message
            services = health.get("services", {})
            failing_services = [
                f"{name}: {status.get('error', 'unknown error')}"
                for name, status in services.items()
                if status.get("status") != "ok"
            ]
            if failing_services and not message:
                message = f"Service issues: {'; '.join(failing_services)}"
            
            # Create response
            response = HealthResponse(
                status=health.get("status", "ok" if is_ready else "not_ready"),
                service_name=service._service_name,
                version=version,
                is_running=True,
                is_ready=is_ready,
                error=error,
                message=message,
                uptime=uptime
            )
            
            # Return 503 if service is not ready
            if not is_ready:
                raise_http_error(
                    AppErrorCode.SERVICE_UNAVAILABLE,
                    response.message or "Service is not ready",
                    health
                )
            
            return response
            
        except ConfigurationError as e:
            raise_http_error(
                AppErrorCode.SERVICE_UNAVAILABLE,
                str(e),
                e.context
            )
        except Exception as e:
            logger.error(f"Service health check failed: {e}")
            raise_http_error(
                AppErrorCode.SERVICE_ERROR,
                f"Service health check failed: {str(e)}"
            )

    @router.post(
        "/control",
        response_model=ControlResponse,
        responses={
            status.HTTP_400_BAD_REQUEST: {
                "description": "Invalid control command",
                "model": dict
            },
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "description": "Service is not available",
                "model": dict
            }
        }
    )
    async def control(request: ControlRequest) -> ControlResponse:
        """Control service state."""
        try:
            if request.action == ServiceAction.START:
                await service.start()
                return ControlResponse(
                    status="success",
                    message=f"{service._service_name} started"
                )
            elif request.action == ServiceAction.STOP:
                await service.stop()
                return ControlResponse(
                    status="success",
                    message=f"{service._service_name} stopped"
                )
            else:  # restart
                await service.restart()
                return ControlResponse(
                    status="success",
                    message=f"{service._service_name} restarted"
                )
        except ServiceError as e:
            return ControlResponse(
                status="error",
                message=f"Failed to {request.action} service",
                error=str(e)
            )
