"""Communication API application."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import yaml
import sys

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
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


def create_communication_service(config: Optional[Dict[str, Any]] = None) -> FastAPI:
    """Create communication service application.
    
    Args:
        config: Optional configuration dictionary. If not provided, will load from file.
    
    Returns:
        FastAPI application instance
    """
    # Load configuration if not provided
    if config is None:
        config = load_config()
    
    # Setup logging
    setup_logging(config["service"]["log_level"])
    logger.info("Starting communication service...")

    # Create FastAPI app
    app = FastAPI(
        title="Communication Service",
        description="Service for hardware communication",
        version=config["version"]
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Add error handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        error_msg = f"Validation error: {str(exc)}"
        logger.error(error_msg)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": "Validation error",
                "details": exc.errors()
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        error_msg = f"Internal server error: {str(exc)}"
        logger.error(error_msg)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": str(exc)
            }
        )

    # Initialize services
    force_mock = config["communication"]["hardware"]["network"]["force_mock"]
    
    # Create PLC client
    if force_mock:
        plc_client = MockPLCClient(config)
    else:
        plc_client = PLCClient(config)
        
    # Create SSH client if configured
    ssh_config = config["communication"]["hardware"]["network"]["ssh"]
    ssh_client = SSHClient(
        host=ssh_config["host"],
        port=ssh_config["port"],
        username=ssh_config["username"],
        password=ssh_config["password"]
    ) if not force_mock else None

    # Create services
    tag_mapping_service = TagMappingService(config)
    tag_cache_service = TagCacheService(config, plc_client, ssh_client, tag_mapping_service)
    motion_service = MotionService(config)
    equipment_service = EquipmentService(config)
    
    # Store services in app state
    app.state.config = config
    app.state.tag_mapping_service = tag_mapping_service
    app.state.tag_cache_service = tag_cache_service
    app.state.motion_service = motion_service
    app.state.equipment_service = equipment_service

    @app.on_event("startup")
    async def startup():
        """Initialize and start all services."""
        try:
            logger.info("Starting communication service...")
            
            # Initialize and start services in order
            await tag_mapping_service.initialize()
            await tag_mapping_service.start()
            
            await tag_cache_service.initialize()
            await tag_cache_service.start()
            
            # Set up motion service dependencies
            motion_service.set_tag_cache(tag_cache_service)
            await motion_service.initialize()
            await motion_service.start()
            
            # Set up equipment service dependencies
            equipment_service.set_tag_cache(tag_cache_service)
            await equipment_service.initialize()
            await equipment_service.start()
            
            logger.info("Communication service started successfully")
            
        except Exception as e:
            logger.error(f"Communication service startup failed: {str(e)}")
            # Don't raise here - let the service start in degraded mode
            # The health check will show which components failed

    @app.on_event("shutdown")
    async def shutdown():
        """Stop all services."""
        try:
            # Stop services in reverse order
            await equipment_service.stop()
            await motion_service.stop()
            await tag_cache_service.stop()
            await tag_mapping_service.stop()
            
            logger.info("Communication service stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop communication service: {str(e)}")
            # Log but don't raise during shutdown

    @app.get("/health")
    async def health_check() -> ServiceHealth:
        """Get service health status."""
        try:
            # Get health status from all services
            tag_mapping_health = await tag_mapping_service.health()
            tag_cache_health = await tag_cache_service.health()
            motion_health = await motion_service.health()
            equipment_health = await equipment_service.health()
            
            # Combine component health from all services
            components = {
                **tag_mapping_health.components,
                **tag_cache_health.components,
                **motion_health.components,
                **equipment_health.components
            }
            
            # Overall status is error if any service is in error
            services_ok = all([
                tag_mapping_health.status == "ok",
                tag_cache_health.status == "ok",
                motion_health.status == "ok",
                equipment_health.status == "ok"
            ])
            
            return ServiceHealth(
                status="ok" if services_ok else "error",
                service="communication",
                version=config["version"],
                is_running=all([
                    tag_mapping_service.is_running,
                    tag_cache_service.is_running,
                    motion_service.is_running,
                    equipment_service.is_running
                ]),
                uptime=min([  # Use shortest uptime as service uptime
                    tag_mapping_service.uptime,
                    tag_cache_service.uptime,
                    motion_service.uptime,
                    equipment_service.uptime
                ]),
                error=None if services_ok else "One or more services in error state",
                components=components
            )
            
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
                components={}
            )

    # Include routers
    app.include_router(state_router)
    app.include_router(equipment_router)
    app.include_router(motion_router)

    return app
