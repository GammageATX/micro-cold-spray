# src/micro_cold_spray/api/process/process_app.py
"""Process API application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.endpoints import (
    process_endpoints,
    pattern_endpoints,
    parameter_endpoints,
    sequence_endpoints
)


def create_process_service() -> FastAPI:
    """Create process service application."""
    # Create FastAPI app
    app = FastAPI(
        title="Process Service",
        description="Service for managing process execution",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Create process service
    service = ProcessService()
    app.state.service = service
    
    # Add endpoints
    app.include_router(process_endpoints.router)
    app.include_router(pattern_endpoints.router)
    app.include_router(parameter_endpoints.router)
    app.include_router(sequence_endpoints.router)
    
    return app
