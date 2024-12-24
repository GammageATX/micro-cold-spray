"""Communication API application."""

from typing import Dict, Any
from fastapi import FastAPI, Depends, status
from loguru import logger
from datetime import datetime

from micro_cold_spray.utils.errors import create_error
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
        description="API for hardware communication and control",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add routers
    app.include_router(
        equipment_router,
        tags=["equipment"]
    )
    app.include_router(
        motion_router,
        tags=["motion"]
    )
    app.include_router(
        tags_router,
        tags=["tags"]
    )
    
    @app.get("/health", tags=["health"])
    async def check_health(
        service: CommunicationService = Depends(get_communication_service)
    ) -> Dict[str, Any]:
        """Check communication service health.
        
        Returns:
            Health status dictionary with service state
        """
        try:
            health_data = await service.health()
            return {
                "status": health_data["status"],
                "timestamp": datetime.now().isoformat(),
                "data": health_data
            }
        except Exception as e:
            logger.error(f"Failed to check communication service health: {str(e)}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to check communication service health",
                context={"error": str(e)}
            )
    
    @app.get("/", tags=["root"])
    async def root() -> Dict[str, Any]:
        """Root endpoint.
        
        Returns:
            API information
        """
        return {
            "name": "Communication API",
            "version": "1.0.0",
            "description": "API for hardware communication and control",
            "docs": "/docs",
            "health": "/health"
        }
    
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
