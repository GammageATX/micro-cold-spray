# src/micro_cold_spray/api/process/process_app.py
"""Process API application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.endpoints import (
    process_router,
    pattern_router,
    parameter_router,
    sequence_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    try:
        logger.info("Starting process service...")
        
        # Get service from app state
        service = app.state.service
        
        # Initialize and start service
        await service.initialize()
        await service.start()
        
        logger.info("Process service started successfully")
        
        yield  # Server is running
        
        # Shutdown
        if hasattr(app.state, "service") and app.state.service.is_running:
            await app.state.service.stop()
            logger.info("Process service stopped")
            
    except Exception as e:
        logger.error(f"Process service startup failed: {e}")
        # Don't raise here - let the service start in degraded mode
        # The health check will show which components failed
        yield
        # Still try to stop service if it exists
        if hasattr(app.state, "service"):
            try:
                await app.state.service.stop()
            except Exception as stop_error:
                logger.error(f"Failed to stop process service: {stop_error}")


def create_process_service() -> FastAPI:
    """Create process service application."""
    app = FastAPI(
        title="Process Service",
        description="Service for managing process execution",
        version="1.0.0",
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
    
    # Create service
    service = ProcessService()
    app.state.service = service
    
    # Add endpoints without prefix
    app.include_router(process_router)
    app.include_router(pattern_router)
    app.include_router(parameter_router)
    app.include_router(sequence_router)
    
    return app
