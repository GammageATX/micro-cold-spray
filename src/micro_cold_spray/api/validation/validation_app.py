"""Validation service application."""

import os
import yaml
from typing import Dict, Any
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
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
        openapi_url="/openapi.json"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize service
    validation_service = ValidationService()
    app.state.service = validation_service
    app.state.config = config
    
    # Create dependency
    async def get_service() -> ValidationService:
        """Get validation service instance.
        
        Returns:
            ValidationService: Validation service instance
        """
        return app.state.service
    
    # Add health check endpoint
    @app.get("/health", response_model=ServiceHealth)
    async def health(service: ValidationService = Depends(get_service)) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Health status
        """
        return await service.health()
    
    # Include validation router
    app.include_router(router)
    
    @app.on_event("startup")
    async def startup():
        """Start validation service."""
        try:
            logger.info("Starting validation service...")
            logger.info("Validation service started successfully")
            
        except Exception as e:
            logger.error(f"Validation service startup failed: {e}")
            # Don't raise here - let the service start in degraded mode
            # The health check will show which components failed
    
    @app.on_event("shutdown")
    async def shutdown():
        """Stop validation service."""
        try:
            logger.info("Stopping validation service...")
            logger.info("Validation service stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop validation service: {e}")
            # Don't raise during shutdown
    
    return app
