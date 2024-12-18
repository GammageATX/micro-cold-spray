"""Base router functionality."""

import os
import psutil
from typing import Dict, Any, Optional, Type, Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException
from loguru import logger
from starlette.middleware.cors import CORSMiddleware

from .service import BaseService
from .configurable import ConfigurableService
from .errors import ErrorCode, format_error
from .exceptions import ServiceError


def create_api_app(
    service_factory: Union[Type[BaseService], Type[ConfigurableService]],
    prefix: str,
    router: APIRouter,
    additional_routers: Optional[list[APIRouter]] = None,
    config_type: Optional[str] = None
) -> FastAPI:
    """Create a FastAPI application with standard configuration.
    
    Args:
        service_factory: Service class to instantiate
        prefix: URL prefix for the API
        router: Main router for the API
        additional_routers: Additional routers to include
        config_type: Type of configuration to load for configurable services
        
    Returns:
        Configured FastAPI application
    """
    
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
    """Get service instance from FastAPI app state.
    
    Args:
        app: FastAPI application instance
        service_type: Expected service type
        
    Returns:
        Service instance
        
    Raises:
        HTTPException: If service is not available or wrong type
    """
    service = getattr(app.state, "service", None)
    if not service or not isinstance(service, service_type):
        error = ErrorCode.SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=error.get_status_code(),
            detail=format_error(error, f"{service_type.__name__} not initialized")["detail"]
        )
    return service


def add_health_endpoints(router: APIRouter, service: BaseService):
    """Add health check endpoints to router."""
    
    @router.get("/health", tags=["health"])
    async def health_check() -> Dict[str, Any]:
        """Get service health status."""
        try:
            # Get service health info
            health_info = await service.check_health()
            
            # Add process info
            process = psutil.Process(os.getpid())
            health_info["process_info"] = {
                "pid": process.pid,
                "memory": process.memory_info().rss / 1024 / 1024,  # MB
                "cpu_percent": process.cpu_percent()
            }
            
            # Add memory usage for backward compatibility
            health_info["memory_usage"] = health_info["process_info"]["memory"]
            
            # Add service info if not present
            if "service_info" not in health_info:
                health_info["service_info"] = {}
            
            # Update service info with standard fields
            health_info["service_info"].update({
                "name": service._service_name,
                "version": service.version,
                "uptime": str(service.uptime) if service.is_running else None,
                "running": service.is_running
            })
            
            # Add uptime for backward compatibility
            if "uptime" not in health_info and service.uptime:
                health_info["uptime"] = str(service.uptime)
            
            # Copy message and error to service_info if present
            if "message" in health_info:
                health_info["service_info"]["message"] = health_info["message"]
            if "error" in health_info:
                health_info["service_info"]["error"] = health_info["error"]
            
            return health_info

        except HTTPException:
            raise
        except ServiceError as e:
            logger.error(f"Health check failed: {e}")
            error = ErrorCode.HEALTH_CHECK_ERROR
            raise HTTPException(
                status_code=500,  # Internal Server Error
                detail=format_error(error, str(e))
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            error = ErrorCode.HEALTH_CHECK_ERROR
            raise HTTPException(
                status_code=500,  # Internal Server Error
                detail=format_error(error, str(e))
            )

    @router.post("/control")
    async def control_service(action: str):
        """Control service operation."""
        try:
            valid_actions = ["start", "stop", "restart"]
            if action not in valid_actions:
                error = ErrorCode.INVALID_ACTION
                raise HTTPException(
                    status_code=error.get_status_code(),
                    detail=format_error(
                        error,
                        f"Invalid action: {action}",
                        {"valid_actions": valid_actions}
                    )
                )

            if action == "stop":
                await service.stop()
                return {"status": "stopped"}
            elif action == "start":
                await service.start()
                return {"status": "started"}
            elif action == "restart":
                await service.stop()
                await service.start()
                return {"status": "restarted"}
        except HTTPException:
            raise
        except ServiceError as e:
            logger.error(f"Failed to {action} service: {e}")
            error = ErrorCode.SERVICE_UNAVAILABLE
            raise HTTPException(
                status_code=error.get_status_code(),
                detail=format_error(error, str(e))
            )
        except Exception as e:
            logger.error(f"Failed to {action} service: {e}")
            error = ErrorCode.INTERNAL_ERROR
            raise HTTPException(
                status_code=error.get_status_code(),
                detail=format_error(error, str(e))
            )
