"""Communication API application."""

import os
from pathlib import Path
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import yaml

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.monitoring import get_uptime
from micro_cold_spray.api.communication.endpoints.equipment import router as equipment_router
from micro_cold_spray.api.communication.endpoints.motion import router as motion_router
from micro_cold_spray.api.communication.endpoints.tags import router as tags_router
from micro_cold_spray.api.communication.communication_service import CommunicationService


def create_app() -> FastAPI:
    """Create communication service application.
    
    Returns:
        FastAPI application instance
    """
    # Load config
    try:
        # Get config directory
        config_dir = Path("config")
        if not config_dir.exists():
            config_dir = Path(__file__).parent.parent.parent.parent.parent / "config"
            
        # Load config
        config_path = config_dir / "communication.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
            
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        # Add paths
        config["paths"] = {
            "config": str(config_dir),
            "tags": str(config_dir / "tags.yaml")
        }
        
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logger.info(f"Loaded config from {config_path}")
            
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Failed to load config: {str(e)}"
        )

    app = FastAPI(
        title="Communication Service",
        description="Service for hardware communication",
        version="1.0.0"
    )

    # Store config in app instance
    app.config = config

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Initialize service with config
    service = CommunicationService(config)
    app.state.service = service

    @app.on_event("startup")
    async def startup():
        """Initialize and start service on startup."""
        try:
            await service.initialize()
            await service.start()
            logger.info("Communication service started")
        except Exception as e:
            logger.error(f"Failed to start communication service: {str(e)}")
            raise

    @app.on_event("shutdown")
    async def shutdown():
        """Stop service on shutdown."""
        try:
            await service.stop()
            logger.info("Communication service stopped")
        except Exception as e:
            logger.error(f"Failed to stop communication service: {str(e)}")
            raise

    @app.get("/health")
    async def health_check():
        """Get service health status."""
        return await service.health()

    # Include routers
    app.include_router(equipment_router)
    app.include_router(motion_router)
    app.include_router(tags_router)

    return app
