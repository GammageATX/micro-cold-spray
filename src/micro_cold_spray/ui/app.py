"""UI service application module."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from loguru import logger

from .utils import get_flashed_messages


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Create FastAPI app
    app = FastAPI(
        title="Micro Cold Spray System Control",
        description="Power user interface for system monitoring and control",
        version="1.0.0"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY", "your-secret-key-here"),  # Change in production
        session_cookie="mcs_session",
        max_age=86400  # 1 day
    )

    # Set up paths
    ui_dir = Path(__file__).parent
    static_dir = ui_dir / "static"
    templates_dir = ui_dir / "templates"

    # Set up template engine
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # Add custom template functions
    templates.env.globals.update({
        "get_flashed_messages": get_flashed_messages
    })
    
    app.state.templates = templates

    # Mount static files
    try:
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    except Exception as e:
        logger.error(f"Failed to mount static files: {e}")

    # Configure API endpoints
    app.state.api_endpoints = {
        "config": os.getenv("CONFIG_SERVICE_URL", "http://localhost:8001"),
        "communication": os.getenv("COMMUNICATION_SERVICE_URL", "http://localhost:8002"),
        "process": os.getenv("PROCESS_SERVICE_URL", "http://localhost:8003"),
        "state": os.getenv("STATE_SERVICE_URL", "http://localhost:8004"),
        "data_collection": os.getenv("DATA_COLLECTION_SERVICE_URL", "http://localhost:8005"),
        "validation": os.getenv("VALIDATION_SERVICE_URL", "http://localhost:8006"),
        "messaging": os.getenv("MESSAGING_SERVICE_URL", "http://localhost:8007")
    }

    # Import and register routes
    from .router import register_routes
    register_routes(app)

    return app


# Create application instance
app = create_app()
