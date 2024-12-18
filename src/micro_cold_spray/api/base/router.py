"""Base router functionality."""

from typing import Optional, Type, Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from .service import BaseService, ConfigurableService


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service_name: str
    version: str
    is_running: bool


def create_api_app(
    service_factory: Union[Type[BaseService], Type[ConfigurableService]],
    prefix: str,
    router: APIRouter,
    additional_routers: Optional[list[APIRouter]] = None,
    config_type: Optional[str] = None
) -> FastAPI:
    """Create a FastAPI application with standard configuration."""
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Standard lifespan context manager for FastAPI app."""
        service = None
        try:
            # Initialize service based on type
            if issubclass(service_factory, ConfigurableService):
                # Import here to avoid circular imports
                from ..config.singleton import get_config_service
                
                # Get shared config service instance
                config_service = get_config_service()
                await config_service.start()
                logger.info("ConfigService started successfully")
                
                # Create and configure service
                service = service_factory(config_service=config_service)
                if config_type:
                    service.set_config_type(config_type)
            else:
                service = service_factory()
            
            # Start the service
            await service.start()
            logger.info(f"{service._service_name} started successfully")
            
            # Store service instance in app state
            app.state.service = service
            
            # Add health endpoints to the main router
            add_health_endpoints(router, service)
            
            # Include routers
            app.include_router(router, prefix=prefix)
            if additional_routers:
                for additional_router in additional_routers:
                    app.include_router(additional_router, prefix=prefix)
            
            logger.info(f"{service._service_name} router initialized")
            
            yield
            
            # Cleanup on shutdown
            logger.info(f"{service._service_name} API shutting down")
            if service:
                try:
                    await service.stop()
                    logger.info(f"{service._service_name} stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping {service._service_name}: {e}")
                finally:
                    app.state.service = None
                    
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            if service:
                try:
                    await service.stop()
                except Exception as stop_error:
                    logger.error(f"Error during cleanup: {stop_error}")
                finally:
                    app.state.service = None
            raise

    # Create FastAPI app with lifespan
    app = FastAPI(lifespan=lifespan)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


def get_service_from_app(app: FastAPI, service_type: Type[BaseService]) -> BaseService:
    """Get service instance from FastAPI app state."""
    service = getattr(app.state, "service", None)
    if not service or not isinstance(service, service_type):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {service_type.__name__} not initialized"
        )
    return service


def add_health_endpoints(router: APIRouter, service: Union[BaseService, ConfigurableService]) -> None:
    """Add standard health check endpoints to router."""
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
        if not service.is_running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{service._service_name} is not running"
            )
        
        return HealthResponse(
            status="ok",
            service_name=service._service_name,
            version=getattr(service, "version", "1.0.0"),
            is_running=service.is_running
        )

    @router.post(
        "/control",
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_400_BAD_REQUEST: {"description": "Invalid control command"},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not available"}
        }
    )
    async def control(command: str):
        """Control service state."""
        try:
            if command == "start":
                await service.start()
                return {"status": "ok", "message": f"{service._service_name} started"}
            elif command == "stop":
                await service.stop()
                return {"status": "ok", "message": f"{service._service_name} stopped"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid command: {command}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e)
            )
