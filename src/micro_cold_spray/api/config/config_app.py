"""Configuration service FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

from micro_cold_spray.api.config.config_service import ConfigService
from micro_cold_spray.api.config.endpoints import router as config_router
from micro_cold_spray.utils.health import ServiceHealth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    config_service = ConfigService()
    await config_service.start()
    app.state.config_service = config_service
    
    yield  # Server is running
    
    # Shutdown
    await config_service.stop()


def create_config_service() -> FastAPI:
    """Create and configure the FastAPI application for the configuration service."""
    app = FastAPI(title="Configuration Service", lifespan=lifespan)

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
