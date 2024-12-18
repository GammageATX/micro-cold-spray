"""Base router functionality.

This module provides core routing functionality for both BaseService (used by Config API)
and ConfigurableService (used by all other APIs).
"""

from typing import Type, Union, TypeVar
from fastapi import FastAPI, APIRouter, HTTPException, status, Body
from pydantic import BaseModel

from .service import BaseService
from .configurable import ConfigurableService

# Type variable for service types
ServiceType = TypeVar('ServiceType', BaseService, ConfigurableService)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service_name: str
    version: str
    is_running: bool


class ControlRequest(BaseModel):
    """Control request model."""
    action: str


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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {service_type.__name__} not initialized"
        )
    return service


def add_health_endpoints(router: APIRouter, service: Union[BaseService, ConfigurableService]) -> None:
    """Add standard health check endpoints to router.
    
    Args:
        router: Router to add endpoints to
        service: Service instance to monitor
    """
    @router.get(
        "/health",
        response_model=HealthResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not running"}
        }
    )
    async def health_check():
        """Check service health status."""
        try:
            health = await service.check_health()
            response = HealthResponse(
                status=health["status"],
                service_name=service._service_name,
                version=health["service_info"]["version"],
                is_running=health["service_info"]["running"]
            )
            
            # Return 503 if service is not running
            if not response.is_running:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service is not running"
                )
            
            return response
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e)
            )

    @router.post(
        "/control",
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_400_BAD_REQUEST: {"description": "Invalid control command"},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not available"}
        }
    )
    async def control(command: str = Body(..., embed=True)):
        """Control service state."""
        valid_commands = ["start", "stop", "restart"]
        if command not in valid_commands:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid command: {command}. Valid commands are {valid_commands}"
            )
        
        try:
            if command == "start":
                await service.start()
                return {"status": "started", "message": f"{service._service_name} started"}
            elif command == "stop":
                await service.stop()
                return {"status": "stopped", "message": f"{service._service_name} stopped"}
            else:  # restart
                await service.restart()
                return {"status": "restarted", "message": f"{service._service_name} restarted"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e)
            )
