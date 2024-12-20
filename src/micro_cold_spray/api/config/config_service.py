"""Configuration service implementation."""

from typing import Dict, Any
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.base import create_error
from micro_cold_spray.api.config.services.cache_service import CacheService
from micro_cold_spray.api.config.services.file_service import FileService
from micro_cold_spray.api.config.services.format_service import FormatService
from micro_cold_spray.api.config.services.registry_service import RegistryService
from micro_cold_spray.api.config.services.schema_service import SchemaService
from micro_cold_spray.api.config.endpoints import get_config_router


def create_config_service() -> FastAPI:
    """Create configuration service.
    
    Returns:
        FastAPI: Configuration service application
    """
    app = FastAPI(title="Configuration Service")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Initialize services
    app.state.cache = CacheService()
    app.state.file = FileService()
    app.state.format = FormatService()
    app.state.registry = RegistryService()
    app.state.schema = SchemaService()

    @app.on_event("startup")
    async def startup():
        """Start all services on startup."""
        services = [
            app.state.cache,
            app.state.file,
            app.state.format,
            app.state.registry,
            app.state.schema
        ]
        for service in services:
            await service.start()
            logger.info(f"Started {service.name} service")

    @app.on_event("shutdown")
    async def shutdown():
        """Stop all services on shutdown."""
        services = [
            app.state.cache,
            app.state.file,
            app.state.format,
            app.state.registry,
            app.state.schema
        ]
        for service in services:
            await service.stop()
            logger.info(f"Stopped {service.name} service")

    # Include config router
    app.include_router(get_config_router())

    return app
