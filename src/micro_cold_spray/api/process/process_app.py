# src/micro_cold_spray/api/process/process_app.py
"""Process API application."""

from fastapi import FastAPI, status
from loguru import logger
import uvicorn

from micro_cold_spray.utils import ServiceHealth, get_uptime
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.endpoints.process_endpoints import process_router
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

    @app.on_event("startup")
    async def startup():
        """Initialize and start service on startup."""
        try:
            await process_service.initialize()
            await process_service.start()
            logger.info("Process API started")
        except Exception as e:
            logger.error(f"Failed to start Process API: {str(e)}")
            raise

    @app.on_event("shutdown")
    async def shutdown():
        """Stop service on shutdown."""
        try:
            await process_service.stop()
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
            health_data = await process_service.health()
            health_data["uptime"] = get_uptime()
            return ServiceHealth(**health_data)
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="process",
                version=process_service.version,
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

    # Include process router
    app.include_router(process_router)

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
