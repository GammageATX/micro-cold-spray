"""Configuration service implementation."""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.config.services import (
    FileService,
    FormatService,
    SchemaService
)
from micro_cold_spray.api.config.endpoints import get_config_router


# Default paths
DEFAULT_CONFIG_PATH = os.path.join(os.getcwd(), "config")
DEFAULT_SCHEMA_PATH = os.path.join(DEFAULT_CONFIG_PATH, "schemas")


class ConfigService:
    """Configuration service."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize service.
        
        Args:
            config: Service configuration
        """
        self._config = config
        self._version = config.get("version", "1.0.0")
        self._is_running = False
        self._start_time = None
        
        # Get config path from environment or use default
        self._config_path = os.getenv("CONFIG_SERVICE_PATH", DEFAULT_CONFIG_PATH)
        logger.info(f"Using config path: {self._config_path}")
        
        # Initialize services
        self._file = FileService(base_path=self._config_path)
        self._format = FormatService()
        self._schema = SchemaService()
        
        logger.info("Config service initialized")

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            logger.info("Initializing config service...")
            
            # Initialize services in order
            await self._file.initialize()
            await self._format.initialize()
            await self._schema.initialize()
            
            logger.info("Config service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize config service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service."""
        try:
            logger.info("Starting config service...")
            
            # Start services in order
            await self._file.start()
            await self._format.start()
            await self._schema.start()
            
            self._is_running = True
            self._start_time = datetime.now()
            logger.info("Config service started successfully")
            
        except Exception as e:
            self._is_running = False
            error_msg = f"Failed to start config service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            logger.info("Stopping config service...")
            
            # Stop services in reverse order
            await self._schema.stop()
            await self._format.stop()
            await self._file.stop()
            
            self._is_running = False
            logger.info("Config service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop config service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Get health from all services
            file_health = await self._file.health()
            format_health = await self._format.health()
            schema_health = await self._schema.health()
            
            # Build component statuses
            components = {}
            for name, health in [
                ("file", file_health),
                ("format", format_health),
                ("schema", schema_health)
            ]:
                if health.components:
                    # If component has sub-components, include them all
                    for comp_name, comp_health in health.components.items():
                        components[f"{name}.{comp_name}"] = comp_health
                else:
                    # Otherwise include the component itself
                    components[name] = ComponentHealth(
                        status=health.status,
                        error=health.error
                    )
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service="config",
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more components in error state",
                components=components
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="config",
                version=self.version,
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                components={
                    "file": ComponentHealth(status="error", error=error_msg),
                    "format": ComponentHealth(status="error", error=error_msg),
                    "schema": ComponentHealth(status="error", error=error_msg)
                }
            )


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
    
    # Initialize service
    config = {"version": "1.0.0"}  # TODO: Load from config file
    service = ConfigService(config)
    app.state.service = service
    
    @app.on_event("startup")
    async def startup():
        """Start service."""
        try:
            # Initialize and start service
            await app.state.service.initialize()
            await app.state.service.start()
            
        except Exception as e:
            logger.error(f"Config service startup failed: {e}")
            # Don't raise here - let the service start in degraded mode
            # The health check will show which components failed
    
    @app.on_event("shutdown")
    async def shutdown():
        """Stop service."""
        try:
            await app.state.service.stop()
            
        except Exception as e:
            logger.error(f"Config service shutdown failed: {e}")
            # Don't raise during shutdown
    
    @app.get("/health", response_model=ServiceHealth)
    async def health_check() -> ServiceHealth:
        """Get service health status."""
        return await app.state.service.health()
    
    # Include config router
    app.include_router(get_config_router())
    
    return app
