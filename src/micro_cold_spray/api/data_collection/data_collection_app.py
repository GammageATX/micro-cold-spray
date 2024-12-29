"""Data collection API application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

from micro_cold_spray.api.data_collection.data_collection_router import router
from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
from micro_cold_spray.api.data_collection.data_collection_storage import DataCollectionStorage
from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    try:
        # Get service from app state
        service = app.state.service
        
        # Initialize and start service
        await service.initialize()
        await service.start()
        
        logger.info("Data collection service started successfully")
        
        yield  # Server is running
        
        # Shutdown
        await app.state.service.stop()
        logger.info("Data collection service stopped successfully")
        
    except Exception as e:
        logger.error(f"Data collection service startup failed: {e}")
        # Don't raise here - let the service start in degraded mode
        # The health check will show which components failed
        yield
        # Still try to stop service if it exists
        if hasattr(app.state, "service"):
            try:
                await app.state.service.stop()
            except Exception as stop_error:
                logger.error(f"Failed to stop data collection service: {stop_error}")


def create_data_collection_service() -> FastAPI:
    """Create data collection application.
    
    Returns:
        FastAPI: Application instance
    """
    app = FastAPI(
        title="Data Collection API",
        description="API for collecting spray data",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
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
    service = DataCollectionService()
    app.state.service = service
    
    # Add routes
    app.include_router(router)
    
    @app.get("/health", response_model=ServiceHealth)
    async def health() -> ServiceHealth:
        """Get API health status."""
        try:
            # Check if service exists and is initialized
            if not hasattr(app.state, "service"):
                return ServiceHealth(
                    status="starting",
                    service="data_collection",
                    version="1.0.0",
                    is_running=False,
                    uptime=0.0,
                    error="Service initializing",
                    mode="normal",
                    components={}
                )
            
            return await app.state.service.health()
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="data_collection",
                version="1.0.0",
                is_running=False,
                uptime=0.0,
                error=error_msg,
                mode="normal",
                components={
                    "storage": {"status": "error", "error": error_msg},
                    "collector": {"status": "error", "error": error_msg}
                }
            )
    
    return app
