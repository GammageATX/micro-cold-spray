"""Communication API application."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import yaml
import sys

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import get_uptime, ServiceHealth, ComponentHealth
from micro_cold_spray.api.communication.endpoints import router as state_router
from micro_cold_spray.api.communication.endpoints.equipment import router as equipment_router
from micro_cold_spray.api.communication.endpoints.motion import router as motion_router
from micro_cold_spray.api.communication.communication_service import CommunicationService


def setup_logging():
    """Setup logging configuration."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Remove default handler
    logger.remove()
    
    # Add console handler with color
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(sys.stderr, format=log_format, level="INFO")
    
    # Add file handler with rotation
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    )
    logger.add(
        str(log_dir / "communication.log"),
        rotation="1 day",
        retention="30 days",
        format=file_format,
        level="DEBUG"
    )


def load_config() -> Dict[str, Any]:
    """Load service configuration.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
        
    Raises:
        HTTPException: If config loading fails
    """
    try:
        config_dir = Path("config")
        config_path = config_dir / "communication.yaml"
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        # Add standard paths
        config["paths"] = {
            "config": str(config_dir),
            "tags": str(config_dir / "tags.yaml"),
            "mock_data": str(config_dir / "mock_data.yaml")
        }
        
        # Add service info
        config["service"] = {
            "name": "communication",
            "version": config.get("version", "1.0.0")
        }
        
        logger.info(f"Loaded config from {config_path}")
        logger.info(f"Using {'mock' if config['communication']['hardware']['network']['force_mock'] else 'hardware'} mode")
        
        return config
            
    except Exception as e:
        error_msg = f"Failed to load config: {str(e)}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg
        )


def create_communication_service(config: Optional[Dict[str, Any]] = None) -> FastAPI:
    """Create communication service application.
    
    Args:
        config: Optional configuration dictionary. If not provided, will load from file.
    
    Returns:
        FastAPI application instance
    """
    # Setup logging
    setup_logging()
    logger.info("Starting communication service...")

    # Load configuration if not provided
    if config is None:
        config = load_config()

    app = FastAPI(
        title="Communication Service",
        description="Service for hardware communication",
        version=config["service"]["version"]
    )

    # Store config and start time in app state
    app.state.config = config
    app.state.start_time = None

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
        """Start service on startup."""
        try:
            await service.start()
            app.state.start_time = datetime.now()
            logger.info("Communication service started")
            
        except Exception as e:
            error_msg = f"Failed to start communication service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    @app.on_event("shutdown")
    async def shutdown():
        """Stop service on shutdown."""
        try:
            await service.stop()
            logger.info("Communication service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop communication service: {str(e)}"
            logger.error(error_msg)
            # Log but don't raise during shutdown

    @app.get("/health", response_model=ServiceHealth)
    async def health_check() -> ServiceHealth:
        """Get service health status."""
        try:
            service_health = await service.health()
            uptime = (datetime.now() - app.state.start_time).total_seconds() if app.state.start_time else 0
            
            # Convert component health to new format
            components = {}
            if service_health and isinstance(service_health, dict):
                for name, component_status in service_health.items():
                    if isinstance(component_status, dict):
                        components[name] = ComponentHealth(
                            status="ok" if component_status.get("status") == "ok" else "error",
                            error=component_status.get("error")
                        )
            
            return ServiceHealth(
                status="ok" if service.is_running else "error",
                service=config["service"]["name"],
                version=config["service"]["version"],
                is_running=service.is_running,
                uptime=uptime,
                error=None if service.is_running else "Service not running",
                mode="mock" if config["communication"]["hardware"]["network"]["force_mock"] else "hardware",
                components=components
            )
        except Exception as e:
            return {
                "status": "error",
                "service": config["service"]["name"],
                "version": config["service"]["version"],
                "is_running": False,
                "uptime": 0,
                "error": str(e),
                "timestamp": datetime.now()
            }

    # Include routers
    app.include_router(state_router)
    app.include_router(equipment_router)
    app.include_router(motion_router)

    return app
