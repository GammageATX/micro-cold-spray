"""Base application module."""

from contextlib import asynccontextmanager
from typing import Type, Optional, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.base.base_errors import (
    create_error,
    SERVICE_ERROR
)


def create_app(
    service_class: Type[BaseService],
    title: str,
    service_name: Optional[str] = None,
    service_dir: Optional[str] = None,
    **kwargs
) -> FastAPI:
    """Create FastAPI application with service.
    
    Args:
        service_class: Service class to initialize
        title: Application title
        service_name: Optional service name
        service_dir: Optional service directory
        **kwargs: Additional FastAPI arguments
        
    Returns:
        FastAPI application
        
    Raises:
        HTTPException: If service fails to start/stop (503)
    """
    # Initialize service
    service = service_class(name=service_name)
    if service_dir:
        service.service_dir = service_dir

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        try:
            # Start service
            await service.start()
            yield
        except Exception as e:
            # Re-raise service errors with proper format
            raise create_error(
                message=f"Failed to start {service.name} service",
                status_code=SERVICE_ERROR,
                context={"service": service.name},
                cause=e
            )
        finally:
            try:
                # Stop service
                if service.is_running:
                    await service.stop()
            except Exception as e:
                # Log stop errors but don't fail
                app.logger.error(
                    f"Failed to stop {service.name} service: {str(e)}"
                )

    # Create FastAPI app
    app = FastAPI(title=title, lifespan=lifespan, **kwargs)
    
    # Store service in state
    app.state.service = service

    # Add router with health check
    router = BaseRouter()
    router.services.append(service)
    app.include_router(router)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600
    )

    return app
