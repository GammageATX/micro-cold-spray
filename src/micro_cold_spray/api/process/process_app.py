# src/micro_cold_spray/api/process/process_app.py
"""Process API application."""

from fastapi import FastAPI, status
from loguru import logger
import uvicorn

from micro_cold_spray.utils import ServiceHealth, get_uptime
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.endpoints.process_endpoints import create_process_router
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus,
    ActionStatus,
    ProcessPattern,
    ParameterSet,
    SequenceMetadata,
    SequenceStep
)


def create_app() -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="Process API",
        description="API for managing process execution",
        version="1.0.0"
    )

    # Initialize service
    process_service = ProcessService()
    app.state.process_service = process_service

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
            logger.info("Process API stopped")
        except Exception as e:
            logger.error(f"Failed to stop Process API: {str(e)}")
            raise

    @app.get("/")
    async def root():
        """Get API information."""
        return {
            "name": "Process API",
            "version": "1.0.0",
            "description": "API for managing process execution",
            "endpoints": [
                "/",
                "/health",
                "/sequences",
                "/sequences/{sequence_id}",
                "/sequences/{sequence_id}/start",
                "/sequences/{sequence_id}/stop",
                "/sequences/{sequence_id}/status"
            ]
        }

    @app.get("/health", response_model=ServiceHealth)
    async def health():
        """Get API health status."""
        try:
            service_health = await app.state.process_service.health()
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
                service="process",
                version=app.state.process_service.version,
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


if __name__ == "__main__":
    # Run server
    uvicorn.run(
        "micro_cold_spray.api.process.process_app:create_app",
        host="0.0.0.0",
        port=8004,
        factory=True,
        reload=True
    )
