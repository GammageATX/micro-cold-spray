"""Configuration service application."""

from fastapi import FastAPI, status
from fastapi.middleware.gzip import GZipMiddleware
from pathlib import Path
from typing import Type

from micro_cold_spray.api.base.base_app import BaseApp
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.endpoints import ConfigRouter


class ConfigApp(BaseApp):
    """Configuration service application."""

    def __init__(
        self,
        config_dir: Path = None,
        enable_metrics: bool = False,
        service_class: Type[BaseService] = ConfigService,
        **kwargs
    ):
        """Initialize config application.
        
        Args:
            config_dir: Configuration directory path
            enable_metrics: Enable metrics endpoint
            service_class: Service class to use (defaults to ConfigService)
            **kwargs: Additional FastAPI arguments
            
        Raises:
            HTTPException: If initialization fails (503)
        """
        try:
            # Initialize base app with service class
            super().__init__(
                service_class=service_class,
                title="Configuration Service",
                service_name="config",
                **kwargs
            )

            # Set config directory if provided
            if config_dir and isinstance(self.state.service, ConfigService):
                self.state.service._config_dir = config_dir
            
            # Add GZip middleware
            self.add_middleware(GZipMiddleware, minimum_size=1000)

            # Initialize endpoints
            config_router = ConfigRouter(self.state.service)
            self.include_router(config_router)

            # Store config dir
            self.config_dir = config_dir
            
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to initialize config application",
                context={"error": str(e)},
                cause=e
            )


def create_app(**kwargs) -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        FastAPI: Application instance
        
    Raises:
        HTTPException: If app creation fails (503)
    """
    try:
        return ConfigApp(**kwargs)
    except Exception as e:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Failed to create config application",
            context={"error": str(e)},
            cause=e
        )
