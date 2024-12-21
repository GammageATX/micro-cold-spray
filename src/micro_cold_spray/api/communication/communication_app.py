"""Communication API application."""

from typing import Dict, Any
from fastapi import FastAPI, Depends, status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.communication_service import CommunicationService
from micro_cold_spray.api.communication.endpoints import equipment_router, motion_router, tags_router
from micro_cold_spray.api.communication.dependencies import initialize_service, cleanup_service, get_communication_service


def create_app() -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="Communication API",
        description="API for hardware communication",
        version="1.0.0"
    )
    
    # Add routers
    app.include_router(equipment_router)
    app.include_router(motion_router)
    app.include_router(tags_router)
    
    @app.get("/health")
    async def check_health(
        service: CommunicationService = Depends(get_communication_service)
    ) -> Dict[str, Any]:
        """Check communication service health.
        
        Returns:
            Health status dictionary
        """
        try:
            return await service.health()
        except Exception as e:
            logger.error(f"Failed to check communication service health: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to check communication service health"
            )
    
    # Add startup/shutdown events
    @app.on_event("startup")
    async def startup():
        """Initialize services on startup."""
        logger.info("Starting communication service")
        await initialize_service()
    
    @app.on_event("shutdown")
    async def shutdown():
        """Clean up services on shutdown."""
        logger.info("Stopping communication service")
        await cleanup_service()
    
    return app
