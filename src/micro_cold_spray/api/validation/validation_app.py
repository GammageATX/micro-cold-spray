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
            health_data = await validation_service.health()
            health_data["uptime"] = get_uptime()
            return ServiceHealth(**health_data)
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="validation",
                version=validation_service.version,
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
    
    return app
