# src/micro_cold_spray/api/process/process_app.py
"""Process API application."""

import os
import yaml
from typing import Dict, Any
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.endpoints.process_endpoints import create_process_router


def load_config() -> Dict[str, Any]:
    """Load process configuration.
    
    Returns:
        Dict[str, Any]: Configuration data
    """
    config_path = os.path.join("config", "process.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {"version": "1.0.0"}


def create_app() -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        FastAPI application
    """
    # Load config
    config = load_config()
    version = config.get("version", "1.0.0")
    
    app = FastAPI(
        title="Process API",
        description="API for managing process execution",
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
    process_service = ProcessService()
    app.state.process_service = process_service
    app.state.config = config

    @app.on_event("startup")
    async def startup():
        """Start process service."""
        try:
            logger.info("Starting process service...")
            
            # Initialize service first
            await app.state.process_service.initialize()
            
            # Then start the service
            await app.state.process_service.start()
            
            logger.info("Process service started successfully")
            
        except Exception as e:
            logger.error(f"Process service startup failed: {e}")
            # Don't raise here - let the service start in degraded mode
            # The health check will show which components failed

    @app.on_event("shutdown")
    async def shutdown():
        """Stop service on shutdown."""
        try:
            await app.state.process_service.stop()
            logger.info("Process service stopped")
        except Exception as e:
            logger.error(f"Failed to stop process service: {str(e)}")
            # Don't raise during shutdown

    @app.get("/health", response_model=ServiceHealth)
    async def health() -> ServiceHealth:
        """Get API health status."""
        try:
            return await app.state.process_service.health()
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="process",
                version=version,
                is_running=False,
                uptime=0.0,
                error=error_msg,
                components={
                    "action": {"status": "error", "error": error_msg},
                    "parameter": {"status": "error", "error": error_msg},
                    "pattern": {"status": "error", "error": error_msg},
                    "sequence": {"status": "error", "error": error_msg}
                }
            )

    # Include process router with service instance
    app.include_router(create_process_router(app.state.process_service))

    return app
