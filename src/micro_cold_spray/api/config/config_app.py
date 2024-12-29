"""Configuration API application."""

import os
import yaml
from typing import Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.endpoints.config_endpoints import router as config_router


def load_config() -> Dict[str, Any]:
    """Load configuration from file.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    try:
        config_path = os.path.join("config", "config.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load config: {e}")
    
    # Return default config if loading fails
    return {
        "version": "1.0.0",
        "mode": "normal",
        "components": {
            "file": {
                "version": "1.0.0"
            },
            "format": {
                "version": "1.0.0"
            },
            "schema": {
                "version": "1.0.0"
            }
        }
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    try:
        logger.info("Starting config service...")
        
        # Get service from app state
        service = app.state.service
        
        # Initialize and start service
        await service.initialize()
        await service.start()
        
        logger.info("Config service started successfully")
        
        yield  # Server is running
        
        # Shutdown
        if hasattr(app.state, "service") and app.state.service.is_running:
            await app.state.service.stop()
            logger.info("Config service stopped")
            
    except Exception as e:
        logger.error(f"Config service startup failed: {e}")
        # Don't raise here - let the service start in degraded mode
        # The health check will show which components failed
        yield
        # Still try to stop service if it exists
        if hasattr(app.state, "service"):
            try:
                await app.state.service.stop()
            except Exception as stop_error:
                logger.error(f"Failed to stop config service: {stop_error}")


def create_config_service() -> FastAPI:
    """Create configuration service application.
    
    Returns:
        FastAPI: Application instance
    """
    # Load config
    config = load_config()
    
    app = FastAPI(
        title="Config API",
        description="API for managing configurations",
        version=config["version"],
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add error handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )
    
    # Create service and router
    service = ConfigService(config)
    app.include_router(config_router)
    
    # Store service in app state
    app.state.service = service
    
    @app.get("/health", response_model=ServiceHealth)
    async def health() -> ServiceHealth:
        """Get service health status."""
        try:
            # Check if service exists and is initialized
            if not hasattr(app.state, "service"):
                return ServiceHealth(
                    status="starting",
                    service="config",
                    version=config["version"],
                    is_running=False,
                    uptime=0.0,
                    error="Service initializing",
                    mode=config.get("mode", "normal"),
                    components={}
                )
            
            return await app.state.service.health()
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="config",
                version=config["version"],
                is_running=False,
                uptime=0.0,
                error=error_msg,
                mode=config.get("mode", "normal"),
                components={
                    "file": {"status": "error", "error": error_msg},
                    "format": {"status": "error", "error": error_msg},
                    "schema": {"status": "error", "error": error_msg}
                }
            )
    
    return app
