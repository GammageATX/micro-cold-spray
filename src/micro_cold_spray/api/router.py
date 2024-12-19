"""Main API router initialization."""

from fastapi import FastAPI, APIRouter
from micro_cold_spray.core.base.router import add_health_endpoints


def init_api_router(app: FastAPI) -> None:
    """Initialize the main API router.
    
    Args:
        app: FastAPI application instance
    """
    # Create root API router
    root_router = APIRouter()
    
    # Add health endpoints at root level
    add_health_endpoints(root_router, app.state.service)
    
    # Include root router
    app.include_router(root_router)
