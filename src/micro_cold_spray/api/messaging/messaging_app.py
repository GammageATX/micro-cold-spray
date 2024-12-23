"""Messaging application."""

from datetime import datetime
from fastapi import FastAPI, status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.ui.utils import get_uptime, get_memory_usage
from .messaging_service import MessagingService
from .messaging_router import router, HealthResponse


class MessagingApp(FastAPI):
    """Messaging application."""
    
    def __init__(self, *args, **kwargs):
        """Initialize application."""
        super().__init__(*args, **kwargs)
        
        # Initialize service
        self.service = MessagingService()
        
        # Add router
        self.include_router(router)
        
        # Add startup and shutdown events
        self.add_event_handler("startup", self.startup_event)
        self.add_event_handler("shutdown", self.shutdown_event)

        # Add health endpoint
        @self.get(
            "/health",
            response_model=HealthResponse,
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not running"}
            }
        )
        async def health_check() -> HealthResponse:
            """Check service health."""
            try:
                return HealthResponse(
                    status="ok" if self.service.is_running else "error",
                    service_name=self.service.name,
                    version=self.service.version,
                    is_running=self.service.is_running,
                    uptime=get_uptime(),
                    memory_usage=get_memory_usage(),
                    error=None if self.service.is_running else "Service not running",
                    timestamp=datetime.now()
                )
            except Exception as e:
                error_msg = f"Health check failed: {str(e)}"
                logger.error(error_msg)
                return HealthResponse(
                    status="error",
                    service_name=self.service.name,
                    version=self.service.version,
                    is_running=False,
                    uptime=0.0,
                    memory_usage={},
                    error=error_msg,
                    timestamp=datetime.now()
                )
        
    async def startup_event(self):
        """Handle startup event."""
        try:
            logger.info("Starting messaging service...")
            await self.service.initialize()
            logger.info("Messaging service started")
        except Exception as e:
            logger.error(f"Failed to start messaging service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start messaging service: {e}"
            )
            
    async def shutdown_event(self):
        """Handle shutdown event."""
        try:
            logger.info("Stopping messaging service...")
            await self.service.stop()
            logger.info("Messaging service stopped")
        except Exception as e:
            logger.error(f"Failed to stop messaging service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop messaging service: {e}"
            )
