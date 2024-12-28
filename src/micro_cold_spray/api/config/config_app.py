"""Configuration service FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import yaml

from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.endpoints import router as config_router
from micro_cold_spray.utils.health import ServiceHealth


def load_config():
    """Load service configuration."""
    try:
        with open("config/config.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config, using defaults: {e}")
        return {
            "version": "1.0.0",
            "service": {
                "host": "0.0.0.0",
                "port": 8001,
                "log_level": "INFO"
            },
            "components": {
                "file": {
                    "version": "1.0.0",
                    "base_path": "config"
                },
                "format": {
                    "version": "1.0.0",
                    "enabled_formats": ["yaml", "json"]
                },
                "schema": {
                    "version": "1.0.0",
                    "schema_path": "config/schemas"
                }
            }
        }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    try:
        # Load config
        config = load_config()
        
        # Create and initialize service
        config_service = ConfigService(version=config["version"])
        await config_service.initialize()
        await config_service.start()
        
        # Store in app state
        app.state.config_service = config_service
        
        logger.info("Configuration service started successfully")
        yield
        
        # Shutdown
        if config_service.is_running:
            await config_service.stop()
            logger.info("Configuration service stopped successfully")
            
    except Exception as e:
        logger.error(f"Service startup failed: {e}")
        yield
        # Still try to stop service if it exists
        if hasattr(app.state, "config_service") and app.state.config_service.is_running:
            try:
                await app.state.config_service.stop()
            except Exception as stop_error:
                logger.error(f"Failed to stop service: {stop_error}")


def create_config_service() -> FastAPI:
    """Create and configure the FastAPI application for the configuration service."""
    app = FastAPI(
        title="Configuration Service",
        description="Service for managing configurations",
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

    # Add error handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    # Add routes
    app.include_router(config_router)

    @app.get("/health", response_model=ServiceHealth)
    async def health_check() -> ServiceHealth:
        """Get service health status."""
        return await app.state.config_service.health()

    return app
