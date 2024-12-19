"""Configuration service application."""

from fastapi import FastAPI
from pathlib import Path

from micro_cold_spray.api.base import BaseApp
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.endpoints import router


class ConfigApp(BaseApp):
    """Configuration service application."""

    def __init__(self, config_dir: Path = None, **kwargs):
        """Initialize config application.
        
        Args:
            config_dir: Configuration directory path
            **kwargs: Additional FastAPI arguments
        """
        super().__init__(
            service_class=ConfigService,
            title="Configuration Service",
            service_name="config",
            enable_cors=True,
            enable_metrics=True,
            **kwargs
        )

        # Include config router
        self.include_router(router)


def create_app(**kwargs) -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        FastAPI: Application instance
    """
    return ConfigApp(**kwargs)
