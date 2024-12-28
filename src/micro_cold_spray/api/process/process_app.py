# src/micro_cold_spray/api/process/process_app.py
"""Process API application."""

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
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.endpoints.process_endpoints import create_process_router
from micro_cold_spray.api.process.models.process_models import (
    ProcessPattern,
    ParameterSet,
    SequenceMetadata,
    SequenceStep,
    Sequence
)


async def load_real_data(service: ProcessService) -> None:
    """Load real data from data directory.
    
    Args:
        service: Process service instance
    """
    # Scan for available patterns
    patterns_dir = os.path.join("data", "patterns")
    pattern_files = [f for f in os.listdir(patterns_dir) if f.endswith(".yaml")]
    logger.info(f"Found {len(pattern_files)} pattern files")

    # Scan for available parameter sets
    params_dir = os.path.join("data", "parameters")
    param_files = [f for f in os.listdir(params_dir) if f.endswith(".yaml") and not os.path.isdir(os.path.join(params_dir, f))]
    logger.info(f"Found {len(param_files)} parameter set files")

    # Scan for available sequences
    sequences_dir = os.path.join("data", "sequences")
    sequence_files = [f for f in os.listdir(sequences_dir) if f.endswith(".yaml")]
    logger.info(f"Found {len(sequence_files)} sequence files")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    try:
        logger.info("Starting process service...")
        
        # Create and initialize service
        process_service = ProcessService()
        await process_service.initialize()
        
        # Load real data from data directory
        await load_real_data(process_service)
        
        # Start the service
        await process_service.start()
        
        # Store in app state and create router
        app.state.process_service = process_service
        app.include_router(create_process_router(process_service))
        
        logger.info("Process service started successfully")
        
        yield  # Server is running
        
        # Shutdown
        await process_service.stop()
        logger.info("Process service stopped")
        
    except Exception as e:
        logger.error(f"Process service startup failed: {e}")
        # Don't raise here - let the service start in degraded mode
        # The health check will show which components failed
        yield
        # Still try to stop service if it exists
        if hasattr(app.state, "process_service"):
            try:
                await app.state.process_service.stop()
            except Exception as stop_error:
                logger.error(f"Failed to stop process service: {stop_error}")


def load_config() -> Dict[str, Any]:
    """Load configuration from file.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    # TODO: Implement config loading
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

    return app
