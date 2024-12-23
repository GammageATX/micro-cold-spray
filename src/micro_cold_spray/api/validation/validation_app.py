"""Validation API application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from micro_cold_spray.api.validation.validation_router import router


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

    # Add validation endpoints
    app.include_router(router)
    
    return app
