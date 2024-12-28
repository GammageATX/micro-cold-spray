"""Validation service application."""

import os
import yaml
from typing import Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.validation.validation_service import ValidationService
from micro_cold_spray.api.validation.validation_router import router


def load_config() -> Dict[str, Any]:
    """Load validation service configuration.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    config_path = os.path.join("config", "validation.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    try:
        logger.info("Starting validation service...")
        
        # Initialize service
        validation_service = ValidationService()
        await validation_service.initialize()
        await validation_service.start()
        app.state.service = validation_service
        
        logger.info("Validation service started successfully")
        
        yield  # Server is running
        
        # Shutdown
        if app.state.service.is_running:
            await app.state.service.stop()
            logger.info("Validation service stopped successfully")
            
    except Exception as e:
        logger.error(f"Validation service startup failed: {e}")
        # Don't raise here - let the service start in degraded mode
        # The health check will show which components failed
        yield
        # Still try to stop service if it exists
        if hasattr(app.state, "service") and app.state.service.is_running:
            try:
                await app.state.service.stop()
            except Exception as stop_error:
                logger.error(f"Failed to stop validation service: {stop_error}")


def create_app() -> FastAPI:
    """Create validation service.
    
    Returns:
        FastAPI: Application instance
    """
    # Load config
    config = load_config()
    version = config.get("version", "1.0.0")
    
    app = FastAPI(
        title="Validation Service",
        description="Service for validating configurations",
        version=version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
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
    
    @app.get("/health", response_model=ServiceHealth)
    async def health() -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Health status
        """
        return await app.state.service.health()
    
    # Include validation router
    app.include_router(router)
    
    return app
