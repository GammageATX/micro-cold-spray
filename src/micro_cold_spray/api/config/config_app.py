"""Configuration service application."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.endpoints import get_config_router


def create_config_service() -> FastAPI:
    """Create configuration service.
    
    Returns:
        FastAPI: Application instance
    """
    # Create FastAPI app
    app = FastAPI(title="Configuration Service")
    
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
    
    # Initialize service
    service = ConfigService()
    app.state.service = service
    
    @app.on_event("startup")
    async def startup():
        """Start service."""
        try:
            await app.state.service.initialize()
            await app.state.service.start()
        except Exception as e:
            logger.error(f"Config service startup failed: {e}")
            # Don't raise here - let the service start in degraded mode
            # The health check will show which components failed
    
    @app.on_event("shutdown")
    async def shutdown():
        """Stop service."""
        try:
            await app.state.service.stop()
        except Exception as e:
            logger.error(f"Config service shutdown failed: {e}")
            # Don't raise during shutdown
    
    @app.get("/health", response_model=ServiceHealth)
    async def health_check() -> ServiceHealth:
        """Get service health status."""
        return await app.state.service.health()
    
    # Include config router
    app.include_router(get_config_router())
    
    return app
