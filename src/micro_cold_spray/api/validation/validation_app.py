"""Validation API application."""

from typing import Dict, Any
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.utils import ServiceHealth, get_uptime
from micro_cold_spray.api.validation.validation_router import router
from micro_cold_spray.api.validation.validation_service import ValidationService


def create_app() -> FastAPI:
    """Create validation service application.
    
    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="Validation Service",
        description="Service for validating configurations",
        version="1.0.0"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Initialize service
    validation_service = ValidationService()
    app.state.service = validation_service

    @app.get("/health", response_model=ServiceHealth)
    async def health_check() -> ServiceHealth:
        """Get service health status."""
        try:
            service_health = await app.state.service.health()
            return ServiceHealth(
                status=service_health.status,
                service=service_health.service,
                version=service_health.version,
                is_running=service_health.is_running,
                uptime=get_uptime(),
                error=service_health.error,
                components=service_health.components
            )
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="validation",
                version="1.0.0",
                is_running=False,
                uptime=0.0,
                error=error_msg,
                components={
                    "hardware_validator": {"status": "error", "error": error_msg},
                    "parameter_validator": {"status": "error", "error": error_msg},
                    "pattern_validator": {"status": "error", "error": error_msg},
                    "sequence_validator": {"status": "error", "error": error_msg}
                }
            )

    # Add validation endpoints
    app.include_router(router)
    
    @app.on_event("startup")
    async def startup():
        """Start validation service."""
        try:
            logger.info("Starting validation service...")
            
            # Initialize service first
            await app.state.service.initialize()
            
            # Then start the service
            await app.state.service.start()
            
            logger.info("Validation service started successfully")
            
        except Exception as e:
            logger.error(f"Validation service startup failed: {e}")
            # Don't raise here - let the service start in degraded mode
            # The health check will show which components failed

    return app
