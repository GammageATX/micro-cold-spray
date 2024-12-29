"""Communication API application."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import yaml
import sys

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth
from micro_cold_spray.api.communication.endpoints import router as state_router
from micro_cold_spray.api.communication.endpoints.equipment import router as equipment_router
from micro_cold_spray.api.communication.endpoints.motion import router as motion_router
from micro_cold_spray.api.communication.services.equipment import EquipmentService
from micro_cold_spray.api.communication.services.motion import MotionService
from micro_cold_spray.api.communication.services.tag_cache import TagCacheService
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService
from micro_cold_spray.api.communication.clients.mock import MockPLCClient
from micro_cold_spray.api.communication.clients.plc import PLCClient
from micro_cold_spray.api.communication.clients.ssh import SSHClient
from micro_cold_spray.api.communication.communication_service import CommunicationService


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration.
    
    Args:
        log_level: Log level to use
    """
    # Remove default handler
    logger.remove()
    
    # Add console handler with color
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(sys.stderr, format=log_format, level=log_level)
    
    # Add file handler with rotation
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
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
        FileNotFoundError: If config file not found
    """
    config_path = Path("config/communication.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    return config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    try:
        logger.info("Starting communication service...")
        
        # Get service from app state
        service = app.state.service
        
        # Initialize and start service
        await service.initialize()
        await service.start()
        
        logger.info("Communication service started successfully")
        
        yield  # Server is running
        
        # Shutdown
        logger.info("Stopping communication service...")
        if hasattr(app.state, "service") and app.state.service.is_running:
            await app.state.service.stop()
            logger.info("Communication service stopped successfully")
        
    except Exception as e:
        logger.error(f"Communication service startup failed: {e}")
        # Don't raise here - let the service start in degraded mode
        # The health check will show which components failed
        yield
        # Still try to stop service if it exists
        if hasattr(app.state, "service"):
            try:
                await app.state.service.stop()
            except Exception as stop_error:
                logger.error(f"Failed to stop communication service: {stop_error}")


def create_communication_service() -> FastAPI:
    """Create communication service application.
    
    Returns:
        FastAPI: Application instance
    """
    # Load config
    config = load_config()
    
    # Setup logging
    setup_logging(config["service"]["log_level"])
    
    app = FastAPI(
        title="Communication Service",
        description="Service for hardware communication",
        version=config["version"],
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
    
    # Create service
    service = CommunicationService(config)
    
    # Add routers
    app.include_router(state_router)
    app.include_router(equipment_router)
    app.include_router(motion_router)
    
    # Store service in app state
    app.state.service = service
    
    @app.get("/health", response_model=ServiceHealth)
    async def health() -> ServiceHealth:
        """Get service health status."""
        try:
            # Check if service exists and is initialized
            if not hasattr(app.state, "service"):
                return ServiceHealth(
                    status="starting",
                    service="communication",
                    version=config["version"],
                    is_running=False,
                    uptime=0.0,
                    error="Service initializing",
                    mode=config.get("mode", "normal"),
                    components={}
                )
            
            return await app.state.service.health()
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="communication",
                version=config["version"],
                is_running=False,
                uptime=0.0,
                error=error_msg,
                mode=config.get("mode", "normal"),
                components={
                    "serial": {"status": "error", "error": error_msg},
                    "protocol": {"status": "error", "error": error_msg}
                }
            )
    
    return app
