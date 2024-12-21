"""Messaging service application."""

from typing import Optional, Dict, Any
from fastapi import FastAPI, status
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.messaging.messaging_service import MessagingService
from micro_cold_spray.api.messaging.messaging_router import router


class MessagingApp(FastAPI):
    """Messaging service application."""

    def __init__(self, **kwargs):
        """Initialize messaging application.
        
        Args:
            **kwargs: Additional FastAPI arguments
            
        Raises:
            HTTPException: If initialization fails (503)
        """
        try:
            # Initialize FastAPI
            super().__init__(
                title="Messaging Service",
                description="Service for handling pub/sub messaging",
                version="1.0.0",
                **kwargs
            )

            # Add GZip middleware
            self.add_middleware(GZipMiddleware, minimum_size=1000)

            # Include router
            self.include_router(router)

            # Initialize service
            self._service: Optional[MessagingService] = None
            
            logger.info("Messaging application initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize messaging application: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to initialize messaging application: {e}"
            )

    @property
    def service(self) -> MessagingService:
        """Get messaging service instance."""
        if not self._service:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Messaging service not initialized"
            )
        return self._service

    async def startup(self) -> None:
        """Start up the application."""
        try:
            # Initialize service
            self._service = MessagingService()
            await self._service.initialize()
            logger.info("Messaging service started")
        except Exception as e:
            logger.error(f"Failed to start messaging service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start messaging service: {e}"
            )

    async def shutdown(self) -> None:
        """Shut down the application."""
        try:
            if self._service:
                await self._service.stop()
                self._service = None
            logger.info("Messaging service stopped")
        except Exception as e:
            logger.error(f"Failed to stop messaging service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop messaging service: {e}"
            )


# Create FastAPI application instance
app = MessagingApp()

# Register startup/shutdown events
app.add_event_handler("startup", app.startup)
app.add_event_handler("shutdown", app.shutdown)


# For backwards compatibility
def create_app(**kwargs) -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        FastAPI: Application instance
        
    Raises:
        HTTPException: If app creation fails (503)
    """
    try:
        return MessagingApp(**kwargs)
    except Exception as e:
        logger.error(f"Failed to create messaging application: {e}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Failed to create messaging application: {e}"
        )
