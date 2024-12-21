"""Messaging application."""

from fastapi import FastAPI, status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from .messaging_service import MessagingService
from .messaging_router import router


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
