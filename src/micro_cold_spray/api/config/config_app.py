"""Configuration service application."""

from fastapi import FastAPI, status
from fastapi.middleware.gzip import GZipMiddleware
from pathlib import Path

from micro_cold_spray.api.base import BaseApp
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.endpoints import ConfigRouter


class ConfigApp(BaseApp):
    """Configuration service application."""

    def __init__(self, config_dir: Path = None, **kwargs):
        """Initialize config application.
        
        Args:
            config_dir: Configuration directory path
            **kwargs: Additional FastAPI arguments
            
        Raises:
            HTTPException: If initialization fails (503)
        """
        try:
            super().__init__(
                service_class=ConfigService,
                title="Configuration Service",
                service_name="config",
                **kwargs
            )

            # Add GZip middleware
            self.add_middleware(GZipMiddleware, minimum_size=1000)

            # Initialize endpoints
            config_router = ConfigRouter(self.service)
            self.include_router(config_router.router)

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
