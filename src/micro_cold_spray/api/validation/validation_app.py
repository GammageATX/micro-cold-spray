"""Validation service application."""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.validation.validation_service import ValidationService
from micro_cold_spray.api.validation.validation_router import router, HealthResponse
from micro_cold_spray.ui.utils import get_uptime, get_memory_usage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for service initialization and cleanup."""
    try:
        # Initialize services
        app.state.message_broker = MessagingService()
        app.state.validation_service = ValidationService()
        
        await app.state.message_broker.initialize()
        await app.state.validation_service.initialize(app.state.message_broker)
        
        logger.info("Validation service initialized")
        
        yield  # Run application
        
        # Cleanup
        if hasattr(app.state, "message_broker"):
            await app.state.message_broker.stop()
        if hasattr(app.state, "validation_service"):
            await app.state.validation_service.stop()
            
        logger.info("Validation service stopped")
        
    except Exception as e:
        logger.error(f"Service lifecycle error: {e}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Service lifecycle error: {str(e)}"
        )


def create_app() -> FastAPI:
    """Create validation service application.
    
    Returns:
        FastAPI application instance
    """
    # Create FastAPI app
    app = FastAPI(
        title="Validation Service",
        description="Service for validating process configurations",
        version="1.0.0",
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Add root health endpoint
    @app.get(
        "/health",
        response_model=HealthResponse,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
        }
    )
    async def health_check() -> HealthResponse:
        """Check service health status."""
        try:
            is_running = app.state.validation_service.is_running
            return HealthResponse(
                status="ok" if is_running else "error",
                service_name="validation",
                version=app.version,
                is_running=is_running,
                uptime=get_uptime(),
                memory_usage=get_memory_usage(),
                error=None if is_running else "Service not running",
                timestamp=datetime.now()
            )
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return HealthResponse(
                status="error",
                service_name="validation",
                version=app.version,
                is_running=False,
                uptime=0.0,
                memory_usage={},
                error=error_msg,
                timestamp=datetime.now()
            )

    # Add validation endpoints
    app.include_router(
        router,
        prefix="/api/validation",
        tags=["validation"]
    )
    
    return app
