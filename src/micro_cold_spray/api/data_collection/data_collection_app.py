"""Data collection API application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from loguru import logger

from micro_cold_spray.api.data_collection.data_collection_router import router
from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
from micro_cold_spray.api.data_collection.data_collection_storage import DataCollectionStorage
from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth


def create_data_collection_app() -> FastAPI:
    """Create data collection application.
    
    Returns:
        FastAPI: Application instance
    """
    app = FastAPI(
        title="Data Collection API",
        description="API for collecting spray data",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize service
    service = DataCollectionService()
    app.state.service = service
    
    # Add routes
    app.include_router(router)
    
    @app.on_event("startup")
    async def startup():
        """Start service."""
        try:
            # Initialize and start service
            await app.state.service.initialize()
            await app.state.service.start()
            
        except Exception as e:
            logger.error(f"Data collection service startup failed: {e}")
            # Don't raise here - let the service start in degraded mode
            # The health check will show which components failed
    
    @app.on_event("shutdown")
    async def shutdown():
        """Stop service."""
        try:
            await app.state.service.stop()
            
        except Exception as e:
            logger.error(f"Data collection service shutdown failed: {e}")
            # Don't raise during shutdown
    
    @app.get("/health", response_model=ServiceHealth)
    async def health() -> ServiceHealth:
        """Get service health status."""
        return await app.state.service.health()
    
    return app
