"""Configuration service implementation."""

import os
from typing import Dict, Any
from datetime import datetime
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.monitoring import get_uptime
from micro_cold_spray.api.config.services import (
    FileService,
    FormatService,
    SchemaService
)
from micro_cold_spray.api.config.endpoints import get_config_router


# Default paths
DEFAULT_CONFIG_PATH = os.path.join(os.getcwd(), "config")
DEFAULT_SCHEMA_PATH = os.path.join(DEFAULT_CONFIG_PATH, "schemas")


def create_config_service() -> FastAPI:
    """Create configuration service.
    
    Returns:
        FastAPI: Application instance
    """
    app = FastAPI(title="Configuration Service")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )
    
    # Get config path from environment or use default
    config_path = os.getenv("CONFIG_SERVICE_PATH", DEFAULT_CONFIG_PATH)
    logger.info(f"Using config path: {config_path}")
    
    # Initialize services
    app.state.file = FileService(base_path=config_path)
    app.state.format = FormatService()
    app.state.schema = SchemaService()
    
    @app.on_event("startup")
    async def startup():
        """Start services."""
        try:
            # Start services
            logger.info("Starting services...")
            await app.state.file.start()
            await app.state.format.start()
            await app.state.schema.start()
            logger.info("All services started successfully")
            
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start config service: {str(e)}"
            )
    
    @app.on_event("shutdown")
    async def shutdown():
        """Stop all services."""
        try:
            logger.info("Stopping services...")
            await app.state.schema.stop()
            await app.state.format.stop()
            await app.state.file.stop()
            logger.info("All services stopped successfully")
            
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop config service: {str(e)}"
            )

    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Get service health status."""
        try:
            # Get health status from all components
            file_health = await app.state.file.health()
            format_health = await app.state.format.health()
            schema_health = await app.state.schema.health()
            
            # Service is healthy if all components are healthy
            is_healthy = all(h["status"] == "ok" for h in [file_health, format_health, schema_health])
            
            return {
                "status": "ok" if is_healthy else "error",
                "service_name": "config",
                "version": "1.0.0",
                "is_running": is_healthy,
                "uptime": get_uptime(),
                "components": {
                    "file": file_health,
                    "format": format_health,
                    "schema": schema_health
                }
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "service_name": "config",
                "version": "1.0.0",
                "is_running": False,
                "uptime": get_uptime(),
                "error": str(e)
            }
    
    # Include config router
    app.include_router(get_config_router())
    
    return app
